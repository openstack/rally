<?xml version="1.0" encoding="UTF-8"?>
<!doctype html>
<html>
    <head>
        <title>${heading["title"]}</title>
        <meta name="generator" content="${generator}">
        <meta charset="utf-8">
        <script type="text/javascript">
            var DOWN = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAGCAYAAAAVMmT4AAAAJUlEQVQYlWNgYGD4TwJmYCBFIYYGFhYWvArx2YAXEK0QWQMGAADd8SPpeGzm9QAAAABJRU5ErkJggg==";
            var NONE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAGCAYAAAAVMmT4AAAADUlEQVQYlWNgGAUIAAABDgAB6WzgmwAAAABJRU5ErkJggg==";
            var UP = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAGCAYAAAAVMmT4AAAAK0lEQVQYlWNgwA7+4xDHqhCGiVaIVwNcAQsLC14N2EzEqoEYhf8ZGBj+AwCZbyPp8zIdEAAAAABJRU5ErkJggg==";

            function sort_table(table_id, col, sort){
                var table = document.getElementById(table_id);
                var tbody = table.tBodies[0];
                var header_row = table.tHead.rows[0];
                render_header(col, sort, header_row);
                sort_results(tbody, col, sort);
            }

            function render_header(col, sort, header_row){
                var h_cells = header_row.cells;
                for(i = 0; i < h_cells.length; i++){
                    var cell = h_cells[i];
                    var img = cell.firstElementChild;
                    if (i == col){
                        if (sort == 1){
                            img.src = UP;
                        }else{
                            img.src = DOWN;
                        }
                    }else{ //spacer image
                        img.src = NONE;
                    }
                }
            }

            function sort_results(tbody, col, sort) {
                var rows = tbody.rows, rlen = rows.length, arr = new Array(), i, j, cells, clen;
                // fill the array with values from the table
                for(i = 0; i < rlen; i++){
                    cells = rows[i].cells;
                    clen = cells.length;
                    arr[i] = new Array();
                    for(j = 0; j < clen; j++){
                        arr[i][j] = cells[j].innerHTML;
                    }
                }
                // sort the array by the specified column number (col) and order (sort)
                arr.sort(function(a, b){
                    return (a[col] == b[col]) ? 0 : ((a[col] > b[col]) ? sort : -1*sort);
                });
                for(i = 0; i < rlen; i++){
                    arr[i] = "<td>"+arr[i].join("</td><td>")+"</td>";
                }
                tbody.innerHTML = "<tr>"+arr.join("</tr><tr>")+"</tr>";
            }
        </script>
        <style type="text/css" media="screen">
            body {
                font-family: verdana, arial, helvetica, sans-serif;
                font-size: 80%;
            }

            table {
                font-size: 100%; width: 100%;
            }

            h1 {
                font-size: 16pt;
                color: gray;
            }

            .heading {
                margin-top: 0ex;
                margin-bottom: 1ex;
            }

            .heading .attribute {
                margin-top: 1ex;
                margin-bottom: 0;
            }

            .heading .description {
                margin-top: 4ex;
                margin-bottom: 6ex;
            }

            #results_table {
                width: 100%;
                border-collapse: collapse;
                border: 1px solid #777;
            }

            #header_row {
                font-weight: bold;
                color: white;
                background-color: #777;
            }

            #results_table td {
                border: 1px solid #777;
                padding: 2px;
            }

            .testcase   { margin-left: 2em;}

            img.updown{
                padding-left: 3px;
                padding-bottom: 2px;
            }

            th:hover{
                cursor:pointer;
            }

            .nowrap {white-space: nowrap;}

        </style>
    </head>

    <body>
        <div class="heading">
            <h1>${heading["title"]}</h1>
            % for name, value in heading["parameters"]:
                <p class="attribute"><strong>${name}:</strong> ${value}</p>
                % endfor
                <p class="description">${heading["description"]}</p>
        </div>

        <table id="results_table">
            <colgroup>
            <col align="left" />
            <col align="left" />
            <col align="left" />
            <col align="left" />
            <col align="left" />
            </colgroup>
            <thead>
            <tr id="header_row">
                <th class="nowrap" onclick="sort_table('results_table', 0, col1_sort); col1_sort *= -1; col2_sort = 1; col3_sort = 1; col4_sort = 1; col5_sort = 1;">Type<img class="updown" src=NONE /></th>
                <th class="nowrap" onclick="sort_table('results_table', 1, col2_sort); col2_sort *= -1; col1_sort = 1; col3_sort = 1; col4_sort = 1; col5_sort = 1;">Field<img class="updown"  src=NONE /></th>
                <th class="nowrap" onclick="sort_table('results_table', 2, col3_sort); col3_sort *= -1; col1_sort = 1; col2_sort = 1; col4_sort = 1; col5_sort = 1;">Value 1<img class="updown" src=NONE /></th>
                <th class="nowrap" onclick="sort_table('results_table', 3, col4_sort); col4_sort *= -1; col1_sort = 1; col2_sort = 1; col3_sort = 1; col5_sort = 1;">Value 2<img class="updown" src=NONE /></th>
                <th onclick="sort_table('results_table', 4, col5_sort); col5_sort *= -1; col1_sort = 1; col2_sort = 1; col3_sort = 1; col4_sort = 1;">Test Name<img class="updown" src=NONE /></th>
            </tr>
            </thead>
            <tbody id="results">
            % for diff in results:
                <tr class="">
                    <td class="type">${diff.get("type")}</td>
                    <td class="field">${diff.get("field", "")}</td>
                    <td class="val">${diff.get("val1", "")}</td>
                    <td class="val">${diff.get("val2", "")}</td>
                    <td class="testname">${diff.get("test_name")}</td>
                </tr>
            % endfor
        </table>
        <script type="text/javascript">
            var col1_sort = 1, col2_sort = 1, col3_sort = 1; col4_sort = 1; col5_sort = 1;
            sort_table("results_table", 4, col5_sort);
            col5_sort *= -1;
        </script>
    </body>
</html>
