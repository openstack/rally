<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

    <head>
        <title>${title}</title>
        <meta name="generator" content="${generator}"/>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
        <style type="text/css" media="screen">
            body {
                    font-family: verdana, arial, helvetica, sans-serif;
                    font-size: 80%;
            }

            table {
                    font-size: 100%; width: 100%;
            }

            pre {
                    font-size: 80%;
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

            a.popup_link {
            }

            a.popup_link:hover {
                color: red;
            }

            .popup_window {
                display: none;
                overflow-x: scroll;
                padding: 10px;
                background-color: #E6E6D6;
                font-family: "Ubuntu Mono", "Lucida Console", "Courier New", monospace;
                text-align: left;
                font-size: 8pt;
            }

            }

            #show_detail_line {
                margin-top: 3ex;
                margin-bottom: 1ex;
            }
            #result_table {
                width: 100%;
                border-collapse: collapse;
                border: 1px solid #777;
            }
            #header_row {
                font-weight: bold;
                color: white;
                background-color: #777;
            }
            #result_table td {
                border: 1px solid #777;
                padding: 2px;
            }
            #total_row  { font-weight: bold; }
            .passClass  { background-color: #6c6; }
            .failClass  { background-color: #c60; }
            .errorClass { background-color: #c00; }
            .passCase   { color: #6c6; }
            .failCase   { color: #c60; font-weight: bold; }
            .errorCase  { color: #c00; font-weight: bold; }
            .hiddenRow  { display: none; }
            .testcase   { margin-left: 2em; }
            td.testname {width: 40%}
            td.small {width: 40px}


        </style>
    </head>

    <body>
        <div class='heading'>
            <h1>${heading['title']}</h1>
            % for name, value in heading['parameters']:
                <p class='attribute'><strong>${name}:</strong> ${value}</p>
                % endfor
                <p class='description'>${heading['description']}</p>
        </div>

        <p id='show_detail_line'>Show
        <a href='#' onclick='showCase(0);return false;'>Summary</a>
        <a href='#' onclick='showCase(1);return false;'>Failed</a>
        <a href='#' onclick='showCase(2);return false;'>All</a>
        </p>
        <table id='result_table'>
            <colgroup>
            <col align='left' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            <col align='right' />
            </colgroup>
            <tr id='header_row'>
                <td>Test Group/Test case</td>
                <td>Count</td>
                <td>Pass</td>
                <td>Fail</td>
                <td>Error</td>
                <td>Skip</td>
                <td>View</td>
                <td> </td>
            </tr>
            <%
            test_class = report['test_class']
            tests_list = report['tests_list']
            cid = test_class['cid']
            count = test_class['count']
            %>
            <tr class="${test_class['style']}">
                <td class="testname">${test_class['desc']}</td>
                <td class="small">${test_class['count']}</td>
                <td class="small">${test_class['Pass']}</td>
                <td class="small">${test_class['fail']}</td>
                <td class="small">${test_class['error']}</td>
                <td class="small">${test_class['skipped']}</td>

                <td class="small"><a href='#' onclick="showClassDetail('${cid}',${count});return false;">Detail</a></td>
                <td> </td>
            </tr>

            % for test in tests_list:

            % if 'output' in test:
              <tr id="${test['tid']}" class="${test['Class']}">
                <td class="${test['style']}"><div class='testcase'>${test['desc']}</div></td>
                <td colspan='7' align='left'>

                <!--css div popup start-->
                <a class="popup_link" onfocus='this.blur();'
                href='javascript:showTestDetail("div_${test['tid']}")' >
                    ${test['status']}</a>

                <div id="div_${test['tid']}" class="popup_window">
                    <div style='text-align: right; color:red;cursor:pointer'>
                    <a onfocus='this.blur();'
                    onclick="document.getElementById('div_${test['tid']}').style.display = 'none' ">
                       [x]</a>
                    </div>
                    <pre>
                    ${test['tid']}: ${test['output']}
                    </pre>
                </div>
                <!--css div popup end-->

                </td>
            </tr>


            % else:
            <tr id="${test['tid']}" class="${test['Class']}">
                <td class="${test['style']}"><div class='testcase'>${test['desc']}</div></td>
                <td colspan='6' align='center'>${test['status']}</td>
            </tr>
            % endif


            % endfor

            <tr id='total_row'>
                <td>Total</td>
                <td>${report['count']}</td>
                <td>${report['Pass']}</td>
                <td>${report['fail']}</td>
                <td>${report['error']}</td>
                <td>${report['skip']}</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
            </tr>
        </table>


        <div>&nbsp;</div>
        <script language="javascript" type="text/javascript">

            /* level - 0:Summary; 1:Failed; 2:All */
            function showCase(level) {
            var trs = document.getElementsByTagName("tr");
            for (var i = 0; i < trs.length; i++){
                switch(trs[i].id.substr(0, 2)) {
                    case "ft":
                    trs[i].className = (level < 1) ? "hiddenRow" : "";
                    break
                    case "pt":
                    trs[i].className = (level > 1) ? "" : "hiddenRow";
                    break
                }
            }
            }

            function getById(id){
                return document.getElementById(id);
            }

            function showClassDetail(cid, count) {
                var id_list = Array(count);
                var toHide = 1;
                for (var i = 0; i < count; i++) {
                    var tid0 = 't' + cid.substr(1) + '.' + (i+1);
                    var tr = getById(tid);
                    var tid = (tr) ? 'f' + tid0 : 'p' + tid0;
                    id_list[i] = tid;
                    if (tr.className) {
                        toHide = 0;
                    }
                }
                for (var i = 0; i < count; i++) {
                    tid = id_list[i];
                    if (toHide) {
                        getById('div_'+tid).style.display = 'none'
                        getById(tid).className = 'hiddenRow';
                    }
                    else {
                        getById(tid).className = '';
                    }
                }
            }

            function showTestDetail(div_id){
                var div = getById(div_id);
                div.style.display = (div.style.display != "block") ? "block" : "none";
            }

            function html_escape(s) {
                return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }

        </script>

    </body>
</html>
