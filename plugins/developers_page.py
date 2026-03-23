# plugins/developers_page.py

from datasette import hookimpl
from datasette.utils.asgi import Response


@hookimpl
def register_routes():
    return [
        (r"^/developers$", developers_page),
        (r"^/llms\.txt$", llms_txt),
    ]


async def _get_databases_info(datasette):
    """Collect database info (names, tables, columns) from the Datasette instance."""
    databases = []
    for db_name in datasette.databases.keys():
        if db_name == "_internal":
            continue

        db = datasette.databases[db_name]
        metadata = datasette.metadata("database", database=db_name) or {}

        tables = []
        try:
            table_names = await db.table_names()
            for table_name in table_names:
                if table_name.startswith("_zeeker"):
                    continue

                table_info = {"name": table_name, "columns": []}
                try:
                    columns = await db.table_columns(table_name)
                    table_info["columns"] = columns
                except Exception:
                    pass

                try:
                    result = await db.execute(
                        f"SELECT COUNT(*) FROM [{table_name}]"
                    )
                    if result.rows:
                        table_info["count"] = result.rows[0][0]
                except Exception:
                    table_info["count"] = None

                tables.append(table_info)
        except Exception:
            tables = []

        database_info = {
            "name": db_name,
            "description": metadata.get("description", ""),
            "tables": tables,
            "table_count": len(tables),
        }
        databases.append(database_info)

    return databases


async def developers_page(request, datasette):
    databases = await _get_databases_info(datasette)

    return Response.html(
        await datasette.render_template(
            "pages/developers.html",
            {
                "databases": databases,
                "request": request,
            },
            request=request,
        )
    )


async def llms_txt(request, datasette):
    databases = await _get_databases_info(datasette)

    lines = [
        "# data.zeeker.sg",
        "> Open legal data platform providing structured access to Singapore legal datasets",
        "",
        "## API",
        "Base URL: https://data.zeeker.sg",
        "",
        "## Endpoints",
        "- GET /{database}/{table}.json - Table data as JSON",
        "- GET /{database}/{table}.csv - Table data as CSV",
        "- GET /{database}.json?sql={query} - Execute SQL query",
        "- GET /-/search.json?q={query} - Full-text search",
        "",
        "## Databases",
    ]

    for db in databases:
        lines.append(f"### {db['name']}")
        if db["description"]:
            lines.append(f"{db['description']}")
        lines.append("Tables:")
        for table in db["tables"]:
            col_list = ", ".join(table["columns"]) if table["columns"] else ""
            count_str = f" ({table['count']} rows)" if table.get("count") else ""
            lines.append(f"- {table['name']}{count_str}: {col_list}")
        lines.append("")

    lines.extend([
        "## Parameters",
        "- _size: Number of rows (default 100, max 1000)",
        "- _next: Pagination token",
        "- _shape: Response shape (objects, arrays, array, object)",
        "- _sort: Sort by column",
        "- _sort_desc: Sort descending by column",
    ])

    content = "\n".join(lines)
    return Response(
        body=content,
        content_type="text/plain; charset=utf-8",
    )
