from datetime import datetime, timezone
import html
import os
import sys
import json
from argparse import ArgumentParser
from logging import basicConfig as logging_basicConfig
from logging import Logger, getLogger
from typing import List

SIMPLE_TYPES = {'string', 'integer', 'boolean', ('string', 'null')}


def main(argv):
    parser = ArgumentParser(description="Extract change tickets from Service Now")
    parser.add_argument('--data_file', required=True, help="JSON source for incident data")
    parser.add_argument('--outfile_markdown', required=True, help="Where to store the markdown docs")
    parser.add_argument('--create_html', action="store_true", help="Create HTML table (Markdown name with .html)")
    parser.add_argument('--schema', required=True, nargs="+", help="JSON schema for the original source values")
    parser.add_argument('--log-level', default='INFO', choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))

    args = parser.parse_args(argv)
    logging_basicConfig(level=args.log_level)
    logger = getLogger(__name__)

    logger.info(f"Starting markdown generation in {os.path.abspath('.')} for:\n{json.dumps(argv, indent=4)}")

    with open(args.data_file, mode="r") as fp:
        data_in = json.load(fp)

    html_out_filename = None
    if args.create_html:
        if args.outfile_markdown.endswith(".md"):
            html_out_filename = args.outfile_markdown[:-3] + ".html"
        else:
            html_out_filename = args.outfile_markdown + ".html"

    raw_schema = eval(" ".join(args.schema))
    if raw_schema['type'] != "array" or raw_schema['items']['type'] != "object":
        logger.error(f"Expected the base element of the schema to be an array.  Got:\n" + json.dumps(raw_schema))
        exit(-1)
    parsed_schema = read_schema_object(raw_schema['items']['properties'])
    main_columns = [one_element['fieldname'] for one_element in parsed_schema]
    logger.debug(f"Parsing for schema {json.dumps(raw_schema)}")

    generation_time_str = datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%MZ')
    with open(args.outfile_markdown, mode="w") as outfile:
        outfile.write("# Incident Descriptions\n")
        outfile.write(f"Generated {generation_time_str}\n\n")
        if html_out_filename:
            if os.path.isabs(html_out_filename):
                logger.warning(f"Not including link to {html_out_filename} because it is an absolute path.\n\n")
            else:
                outfile.write(f"View HTML table [here]({html_out_filename}).  "
                              f"It won't display directly from GitHub; "
                              f"download it and open the html file with your browser.\n\n")
        outfile.write("| " + " | ".join([col.replace("_", " ") for col in main_columns]) + " |\n")
        outfile.write("| " + " | ".join(["---" for _ in main_columns]) + " |\n")
        for one_data in data_in:
            logger.debug(f">>> {json.dumps(one_data)}")
            if set(one_data.keys()) != set(main_columns):
                for expected_col in main_columns:
                    if expected_col not in set(one_data.keys()):
                        one_data[expected_col] = None
                if set(one_data.keys()) != set(main_columns):
                    surprises = [colname for colname in one_data.keys() if colname not in set(main_columns)]
                    logger.error(f"Unexpected values provided for ID {one_data['id']}: {surprises}")
                    exit(-2)
            col_html = html_from_schema(schema=parsed_schema,
                                        data=one_data,
                                        markdown_safe=True,
                                        max_textwidth=20,
                                        include_blanks=True,
                                        include_fieldnames=False,
                                        logger=logger)
            outfile.write("| " + " | ".join(col_html) + " |\n")
        if args.schema:
            ready_for_markdown_schema = raw_schema
            outfile.write("\n# Original Data Schema\n\n")
            outfile.write("The current documentation schema is defined in "
                          "[roles/documentation/defaults/main.yaml](roles/documentation/defaults/main.yaml)\n")
            outfile.write("```json\n")
            outfile.write(f"{json.dumps(ready_for_markdown_schema, indent=4)}\n")
            outfile.write("```\n")

    if html_out_filename:
        logger.info(f"Creating HTML out at {html_out_filename}")
        with open(html_out_filename, mode="w") as html_outfile:
            html_outfile.write("<!doctype html>\n")
            html_outfile.write("<html>\n")
            html_outfile.write('<head>\n')
            html_outfile.write('<meta charset="utf-8" />\n')
            html_outfile.write(f'<style>{get_html_style()}</style>')
            html_outfile.write('<title>Incident Descriptions</title>\n')
            html_outfile.write('</head>\n')
            html_outfile.write("<body>\n")
            html_outfile.write("<h1>Incident Descriptions</h1>\n")
            html_outfile.write("<table>\n")
            html_outfile.write(f"<caption>Incidents parsed at {generation_time_str}</caption>\n")
            html_outfile.write("<thead><tr>\n")
            html_outfile.write("".join([f'<th scope="col">{col.replace("_", " ")}</th>\n'
                                        for col in main_columns]))
            html_outfile.write("</tr></thead><tbody>\n")
            for one_data in data_in:
                col_html = html_from_schema(schema=parsed_schema,
                                            data=one_data,
                                            markdown_safe=False,
                                            max_textwidth=55,
                                            include_blanks=True,
                                            include_fieldnames=False,
                                            logger=logger)
                tagged_col_html = [f'<td class="{fieldname}">{one_col}</td>'
                                   for one_col, fieldname in zip(col_html, main_columns)]
                html_outfile.write("<tr>\n  " + "\n  ".join(tagged_col_html) + "</tr>\n")
            html_outfile.write("</tbody>\n")
            html_outfile.write("</body>\n")
            html_outfile.write("</html>\n")


def read_schema_object(raw_schema: dict) -> list:
    """ Parse the schema into a predictable order of elements.
    """
    processed = list()
    for fieldname, curr_info in raw_schema.items():
        curr_type = curr_info['type']
        if isinstance(curr_type, list):
            curr_type = tuple(curr_type)  # for type selections like ["string", "null"]
        if curr_type in SIMPLE_TYPES:
            type_detail = curr_info.get("enum", [])
        elif curr_type == "object":
            type_detail = read_schema_object(curr_info['properties'])
        elif curr_type == "array":
            item_type = curr_info['items']['type']
            if item_type in SIMPLE_TYPES:
                type_detail = item_type
            elif item_type == "object":
                type_detail = read_schema_object(curr_info['items']['properties'])
            elif item_type == "array" and curr_info['items']['items']['type'] in SIMPLE_TYPES:
                # TODO This is a hack for now to handle an array of arrays of strings
                type_detail = 'string'
            else:
                raise Exception(f"Not currently handling schema arrays of type {item_type}")
        else:
            raise Exception(f"Not currently handling schema data type '{curr_type}'")
        processed.append({"fieldname": fieldname,
                          "type": curr_type,
                          "type_detail": type_detail
                          })
    return processed


def html_from_schema(schema: list,
                     data: dict,
                     markdown_safe: bool,
                     max_textwidth: int,
                     include_blanks: bool,
                     include_fieldnames: bool,
                     logger: Logger) -> list[str]:
    html_out = list()

    for curr_info in schema:
        curr_fieldname = curr_info['fieldname']
        curr_data = data.get(curr_fieldname)
        if not curr_data:
            if include_blanks:
                html_out.append("")
            continue
        curr_type = curr_info['type']
        if curr_type in SIMPLE_TYPES:
            safe_contents = make_string_safe(markdown_safe=markdown_safe,
                                             original=str(curr_data),
                                             max_textwidth=max_textwidth)
            if include_fieldnames:
                html_out.append("<b>"+html.escape(curr_fieldname)+"</b>: "+safe_contents)
            else:
                html_out.append(safe_contents)
        elif curr_type == 'object':
            object_content = html_from_schema(schema=curr_info['type_detail'],
                                              data=curr_data,
                                              markdown_safe=markdown_safe,
                                              max_textwidth=max_textwidth,
                                              include_blanks=False,
                                              include_fieldnames=True,
                                              logger=logger)
            html_out.append("<b>"+html.escape(curr_fieldname)+"</b><ul><li>" +
                            "</li><li>".join(object_content)+"</li></ul>")
        elif curr_type == 'array':
            if isinstance(curr_info['type_detail'], str) \
                    and curr_info['type_detail'] in SIMPLE_TYPES:
                list_strings = [make_string_safe(markdown_safe=markdown_safe,
                                                 original=str(one_elt),
                                                 max_textwidth=max_textwidth)
                                for one_elt in curr_data]
            elif isinstance(curr_info['type_detail'], list) \
                    and curr_info['type_detail'] == {"array"}:
                # TODO: This isn't very pretty yet.  Fix if you have a minute.
                list_strings = [", ".join([make_string_safe(markdown_safe=markdown_safe,
                                                            original=str(sub_elt),
                                                            max_textwidth=max_textwidth)
                                           for sub_elt in one_elt])
                                for one_elt in curr_data]
            else:
                list_content = [html_from_schema(schema=curr_info['type_detail'],
                                                 data=one_elt,
                                                 markdown_safe=markdown_safe,
                                                 max_textwidth=max_textwidth,
                                                 include_blanks=False,
                                                 include_fieldnames=True,
                                                 logger=logger)
                                for one_elt in curr_data]
                list_strings = [f"<b>{html.escape(curr_fieldname)}[{block_idx}]</b><ul><li>" +
                                "</li><li>".join(one_content) +
                                "</li></ul>"
                                for block_idx, one_content in enumerate(list_content)]
            if include_fieldnames:
                html_out.append(html.escape(curr_fieldname)+"<ol><li>"+"</li><li>".join(list_strings)+"</li></ol>")
            else:
                html_out.append("<ol><li>"+"</li><li>".join(list_strings)+"</li></ol>")
        else:
            raise Exception(f"Did not expect schama element '{curr_type}'")
    return html_out


def make_string_safe(markdown_safe: bool, original: str, max_textwidth: int):
    fixed = original

    if markdown_safe:
        fixed = fixed.replace("\n", "\\n")  # newlines don't embed well in markdown

    if len(fixed) > max_textwidth:
        if markdown_safe:
            fixed = f'<span title="{html.escape(fixed)}">{html.escape(fixed[:max_textwidth-3])}...\u2295</span>'
        else:  # Expand in place, rather than with a title-hover
            fixed = f'<span formatted_content="{html.escape(fixed)}">{html.escape(fixed[:max_textwidth-3])}...\u2295</span>'
    else:
        fixed = html.escape(fixed)
    return fixed


def get_html_style():
    return """
        table {
          border-collapse: collapse;
          border: 2px solid rgb(0 58 109);
          font-family: sans-serif;
        }
        caption { caption-side: bottom; padding: 10px; font-weight: bold; }
        thead, tfoot { background-color: rgb(17 146 232); border: 2px solid rgb(0 58 109); }
        th, td { border: 1px solid rgb(51 177 255); padding: 8px 10px; width: min-content }
        th.fault, td.fault { width: max-content }
        td:last-of-type { text-align: center; }
        tbody > tr:nth-of-type(even) { background-color: rgb(130 207 255); }
        tfoot th { text-align: right; }
        tfoot td { font-weight: bold; }
        span:hover::after {
          content: '\\A' attr(formatted_content);
          font: monospace; white-space: pre; font-size: 0.7rem; line-height: 0.7;
          color: rgb(0 65 68);
        }
    """


if __name__ == "__main__":
    main(sys.argv[1:])
