#!/usr/bin/env python3
"""
trim_database.py – Reduce a WGER SQLite dump to a tiny demo size.

Features
--------
* Copies the original database so the source remains untouched.
* Removes non-English rows (assumes English has `id = 2` in `core_language`).
* Ensures every table contains **≤ N rows** (default 100) by intelligently sampling
  rows to keep, preserving referential integrity.
* Tables are processed in dependency order to minimize data loss.
* Re-runs an automatic "FK clean-up" loop as a final safety check.

The script relies solely on the SQLite standard library – no external
dependencies.

Usage
-----
$ python utils/trim_database.py /path/to/wger_database.sqlite  
$ python utils/trim_database.py /path/to/wger_database.sqlite \
      --out-db demo.sqlite --max-rows 50 --verbose
"""
import argparse
import os
import random
import shutil
import sqlite3
import sys
from collections import defaultdict
from typing import Dict, List, Sequence, Set, Tuple

# Optional dependency for YAML export.
try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def copy_database(src: str, dst: str, overwrite: bool = False) -> None:
    """Copy *src* to *dst*.  Abort if *dst* exists and *overwrite* is False."""
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("Destination path must differ from source path")

    if os.path.exists(dst) and not overwrite:
        raise FileExistsError(f"{dst} already exists (use --overwrite to replace)")

    shutil.copy(src, dst)


def get_all_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    return [row[0] for row in cur.fetchall()]


def get_pk_column(conn: sqlite3.Connection, table: str) -> str:
    """Return the name of the single-column primary key or raise if none/compound."""
    cur = conn.execute(f"PRAGMA table_info({table});")
    pk_cols = [row[1] for row in cur.fetchall() if row[5]]  # row[5] == 1 → part of PK
    if len(pk_cols) == 1:
        return pk_cols[0]
    raise ValueError(f"Table {table} has no single-column PK – skipping")


def has_language_id(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    return any(row[1] == "language_id" for row in cur.fetchall())


def delete_non_english_rows(conn: sqlite3.Connection, english_id: int, verbose: bool = False) -> None:
    tables = get_all_tables(conn)
    for tbl in tables:
        if has_language_id(conn, tbl):
            if verbose:
                print(f"Filtering non-English rows in {tbl}…")
            conn.execute(
                f"DELETE FROM {tbl} WHERE language_id IS NOT NULL AND language_id <> ?;",
                (english_id,),
            )
    # Finally, drop other languages themselves.
    if "core_language" in tables:
        conn.execute("DELETE FROM core_language WHERE id <> ?;", (english_id,))
    conn.commit()


def get_foreign_keys(conn: sqlite3.Connection, table: str) -> List[Tuple[str, str, str]]:
    """Get foreign key relationships for a table.
    
    Returns a list of tuples (from_col, to_table, to_col) for each FK constraint.
    """
    cur = conn.execute(f"PRAGMA foreign_key_list({table});")
    return [(row[3], row[2], row[4]) for row in cur.fetchall()]


def build_dependency_graph(conn: sqlite3.Connection) -> Dict[str, Set[str]]:
    """Build a graph of table dependencies based on foreign keys.
    
    Returns a dict mapping table names to sets of tables they depend on.
    """
    tables = get_all_tables(conn)
    graph: Dict[str, Set[str]] = defaultdict(set)
    
    for table in tables:
        fks = get_foreign_keys(conn, table)
        for _, referenced_table, _ in fks:
            graph[table].add(referenced_table)
        
        # Special handling for translations - they should be processed before exercises
        if table == 'exercises_translation':
            graph['exercises_exercise'].add(table)
    
    return graph


def find_strongly_connected_components(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Find strongly connected components (cycles) in the dependency graph using Tarjan's algorithm."""
    index_counter = [0]
    index = {}
    lowlink = {}
    stack = []
    on_stack = set()
    components = []

    def strongconnect(node: str) -> None:
        index[node] = index_counter[0]
        lowlink[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack.add(node)

        # Consider successors of node
        for successor in graph.get(node, set()):
            if successor not in index:
                # Successor has not yet been visited; recurse on it
                strongconnect(successor)
                lowlink[node] = min(lowlink[node], lowlink[successor])
            elif successor in on_stack:
                # Successor is in stack and hence in the current SCC
                lowlink[node] = min(lowlink[node], index[successor])

        # If node is a root node, pop the stack and generate an SCC
        if lowlink[node] == index[node]:
            component = []
            while True:
                successor = stack.pop()
                on_stack.remove(successor)
                component.append(successor)
                if successor == node:
                    break
            components.append(component)

    for node in graph:
        if node not in index:
            strongconnect(node)

    return components


def sort_with_cycles(graph: Dict[str, Set[str]]) -> List[str]:
    """Sort tables handling cycles by collapsing strongly connected components.
    
    Returns a list of tables in a processing order that minimizes the impact
    of circular dependencies.
    """
    # Find strongly connected components (including cycles)
    components = find_strongly_connected_components(graph)
    
    # Create a new graph of components
    component_graph: Dict[int, Set[int]] = defaultdict(set)
    node_to_component: Dict[str, int] = {}
    
    # Map nodes to their component
    for i, component in enumerate(components):
        for node in component:
            node_to_component[node] = i
    
    # Create edges between components
    for i, component in enumerate(components):
        for node in component:
            for successor in graph.get(node, set()):
                succ_component = node_to_component[successor]
                if succ_component != i:  # Don't add self-loops
                    component_graph[i].add(succ_component)
    
    # Topologically sort components
    sorted_components = []
    visited = set()
    
    def visit_component(comp_idx: int) -> None:
        if comp_idx in visited:
            return
        visited.add(comp_idx)
        for dep in component_graph.get(comp_idx, set()):
            visit_component(dep)
        sorted_components.append(comp_idx)
    
    for comp_idx in component_graph:
        if comp_idx not in visited:
            visit_component(comp_idx)
    
    # Flatten the result, reversing component order for correct dependencies
    result = []
    for comp_idx in reversed(sorted_components):
        result.extend(components[comp_idx])
    
    return result


def get_referenced_ids(conn: sqlite3.Connection, table: str, pk_col: str) -> Set[int]:
    """Get all IDs from table that are referenced by foreign keys in other tables."""
    referenced_ids: Set[int] = set()
    
    # Get all tables
    tables = get_all_tables(conn)
    
    # For each table, check if it references our target table
    for other_table in tables:
        if other_table == table:
            continue
            
        fks = get_foreign_keys(conn, other_table)
        for from_col, to_table, to_col in fks:
            if to_table == table and to_col == pk_col:
                # Get all distinct values of the foreign key column
                cur = conn.execute(
                    f"SELECT DISTINCT {from_col} FROM {other_table} WHERE {from_col} IS NOT NULL;"
                )
                referenced_ids.update(row[0] for row in cur.fetchall())
    
    return referenced_ids


def limit_table_rows(
    conn: sqlite3.Connection,
    max_rows: int,
    rng: random.Random,
    verbose: bool = False,
) -> None:
    """Limit rows in tables while preserving referential integrity.
    
    Tables are processed in an order that handles circular dependencies.
    """
    # Build dependency graph and get processing order
    graph = build_dependency_graph(conn)
    table_order = sort_with_cycles(graph)
    
    if verbose:
        print("Processing tables in order:", ", ".join(table_order))
    
    # Track which rows we've decided to keep, to help with circular references
    kept_rows: Dict[str, Set[int]] = defaultdict(set)
    
    for tbl in table_order:
        # Skip exercises_translation table completely
        if tbl == 'exercises_translation':
            continue

        try:
            pk = get_pk_column(conn, tbl)
        except ValueError:
            # Skip tables without a simple integer PK
            continue

        cur = conn.execute(f"SELECT COUNT(*) FROM {tbl};")
        (count,) = cur.fetchone()
        if count <= max_rows:
            # If table is small enough, keep all rows and record them
            cur = conn.execute(f"SELECT {pk} FROM {tbl};")
            kept_rows[tbl].update(row[0] for row in cur.fetchall())
            continue

        # First, get all IDs referenced by foreign keys in tables we've processed
        referenced_ids = get_referenced_ids(conn, tbl, pk)
        
        # Also consider rows that reference IDs we've decided to keep
        fks = get_foreign_keys(conn, tbl)
        for from_col, to_table, to_col in fks:
            if to_table in kept_rows:
                cur = conn.execute(
                    f"SELECT {pk} FROM {tbl} WHERE {from_col} IN ({','.join('?' for _ in kept_rows[to_table])});",
                    tuple(kept_rows[to_table])
                )
                referenced_ids.update(row[0] for row in cur.fetchall())
        
        # Special handling for translations and exercises
        force_limit = tbl in {'exercises_translation', 'exercises_exercise'}
        
        # If we have more referenced IDs than max_rows and we're not forcing limits,
        # we have to keep them all
        if len(referenced_ids) >= max_rows and not force_limit:
            if verbose:
                print(f"Warning: {tbl} has {len(referenced_ids)} referenced rows > max_rows ({max_rows})")
            kept_rows[tbl] = referenced_ids
            continue
            
        # For forced limit tables or normal tables, sample from all IDs
        if force_limit:
            # Get all IDs
            cur = conn.execute(f"SELECT {pk} FROM {tbl};")
            all_ids = [row[0] for row in cur.fetchall()]
            # Randomly sample to max_rows
            keep = set(rng.sample(all_ids, min(max_rows, len(all_ids))))
        else:
            # Get all non-referenced IDs
            cur = conn.execute(
                f"SELECT {pk} FROM {tbl} WHERE {pk} NOT IN ({','.join('?' for _ in referenced_ids)});",
                tuple(referenced_ids)
            )
            unreferenced_ids = [row[0] for row in cur.fetchall()]
            
            # Randomly sample from unreferenced IDs to fill up to max_rows
            remaining_slots = max_rows - len(referenced_ids)
            if remaining_slots > 0:
                keep_unreferenced = set(rng.sample(unreferenced_ids, min(remaining_slots, len(unreferenced_ids))))
            else:
                keep_unreferenced = set()
                
            # Combine referenced and sampled unreferenced IDs
            keep = referenced_ids | keep_unreferenced
            
        kept_rows[tbl] = keep
        
        if verbose:
            print(f"Trimming {tbl}: {count} → {len(keep)} rows")
        
        # Delete rows not in our keep set
        placeholders = ",".join("?" * len(keep))
        conn.execute(f"DELETE FROM {tbl} WHERE {pk} NOT IN ({placeholders});", tuple(keep))
    
    conn.commit()


def fk_cleanup(conn: sqlite3.Connection, max_passes: int = 10, verbose: bool = False) -> None:
    """Iteratively delete rows that violate foreign-key constraints."""
    for i in range(max_passes):
        violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        if not violations:
            if verbose:
                print("Foreign-key check passed.")
            return

        if verbose:
            print(f"Foreign-key violations detected (pass {i + 1}): {len(violations)} rows")
        for tbl, rowid, _parent, _fkid in violations:
            conn.execute(f"DELETE FROM {tbl} WHERE rowid = ?;", (rowid,))
        conn.commit()
    raise RuntimeError("Unable to resolve all foreign-key violations after cleanup loop")


def table_rows_as_dicts(conn: sqlite3.Connection, table: str) -> List[dict]:
    cur = conn.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cur.fetchall()]
    cur = conn.execute(f"SELECT * FROM {table};")
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def dump_database_yaml(conn: sqlite3.Connection, dest: str, verbose: bool = False) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML not installed – install with `pip install pyyaml` to use --dump-yaml")

    if verbose:
        print(f"Dumping trimmed database to YAML: {dest}")

    data: dict[str, List[dict]] = {}
    for tbl in get_all_tables(conn):
        data[tbl] = table_rows_as_dicts(conn, tbl)

    with open(dest, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Shrink the WGER SQLite DB for demos")
    parser.add_argument("src_db", help="Path to the original SQLite database")
    parser.add_argument(
        "--out-db",
        "-o",
        dest="out_db",
        help="Destination path (defaults to <src>_trimmed.sqlite)",
    )
    parser.add_argument(
        "--max-rows",
        "-n",
        type=int,
        default=100,
        help="Maximum rows to keep per table (default: 100)",
    )
    parser.add_argument(
        "--english-id",
        type=int,
        default=2,
        help="ID of English in core_language (default: 2)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite destination if exists")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--dump-yaml",
        "-y",
        nargs="?",
        dest="dump_yaml",
        const=True,
        help="Also dump the trimmed DB to YAML. Optionally provide path; default is <out_db>_dump.yaml",
    )

    args = parser.parse_args(argv)

    src_db = args.src_db
    out_db = args.out_db or (os.path.splitext(src_db)[0] + "_trimmed.sqlite")

    rng = random.Random(args.seed)

    if args.verbose:
        print(f"Copying database: {src_db} → {out_db}")
    copy_database(src_db, out_db, overwrite=args.overwrite)

    conn = sqlite3.connect(out_db)

    # Temporarily disable FK checks while we prune rows; we will resolve
    # violations explicitly afterwards via fk_cleanup().
    conn.execute("PRAGMA foreign_keys = OFF;")

    if args.verbose:
        print("Removing non-English rows…")
    delete_non_english_rows(conn, args.english_id, verbose=args.verbose)

    if args.verbose:
        print("Limiting table sizes…")
    limit_table_rows(conn, args.max_rows, rng, verbose=args.verbose)

    # Re-enable FK enforcement and clean up anything that broke.
    conn.execute("PRAGMA foreign_keys = ON;")

    if args.verbose:
        print("Cleaning up FK violations…")
    fk_cleanup(conn, verbose=args.verbose)

    # Optionally dump to YAML before vacuum (doesn't matter but avoids double-open)
    if args.dump_yaml is not None:
        dump_path = (
            args.dump_yaml if isinstance(args.dump_yaml, str) and args.dump_yaml is not True else os.path.splitext(out_db)[0] + "_dump.yaml"
        )
        dump_database_yaml(conn, dump_path, verbose=args.verbose)

    if args.verbose:
        print("Running VACUUM…")
    conn.execute("VACUUM;")
    conn.close()

    if args.verbose:
        msg = f"Done! Reduced database saved to {out_db}"
        if args.dump_yaml is not None:
            msg += f"; YAML dump at {dump_path}"
        print(msg)


if __name__ == "__main__":
    main() 