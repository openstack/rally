<!doctype html>
<html<%block name="html_attr"/>>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rally | <%block name="title_text"/></title>
  <%block name="libs"/>
  <script type="text/javascript"><%block name="js_before"/></script>
  <style>
    body { margin:0; padding:0 0 50px; font-size:14px; font-family:Helvetica,Arial,sans-serif }
    a, a:active, a:focus, a:visited { text-decoration:none; outline:none }
    p { margin:0; padding:5px 0 }
    p.thesis { padding:10px 0 }
    h1 { color:#666; margin:0 0 20px; font-size:30px; font-weight:normal }
    h2 { color:#777; margin:20px 0 10px; font-size:25px; font-weight:normal }
    h3 { color:#666; margin:13px 0 4px; font-size:18px; font-weight:normal }
    table { border-collapse:collapse; border-spacing:0; width:100%; font-size:12px; margin:0 0 10px }
    table th { text-align:left; padding:8px; color:#000; border:2px solid #ddd; border-width:0 0 2px 0 }
    table th.sortable { cursor:pointer }
    table td { text-align:left; border-top:1px solid #ddd; padding:8px; color:#333 }
    table.compact td { padding:4px 8px }
    table.striped tr:nth-child(odd) td { background:#f9f9f9 }
    table.linked tbody tr:hover { background:#f9f9f9; cursor:pointer }
    .richcolor td { color:#036; font-weight:bold }
    .rich, .rich td { font-weight:bold }
    .code { padding:10px; font-size:13px; color:#333; background:#f6f6f6; border:1px solid #e5e5e5; border-radius:4px }

    .header { text-align:left; background:#333; font-size:18px; padding:13px 0; margin-bottom:20px; color:#fff; background-image:linear-gradient(to bottom, #444 0px, #222 100%) }
    .header a, .header a:visited, .header a:focus { color:#999 }

    .notify-error { padding:5px 10px; background:#fee; color:red }
    .status-skip, .status-skip td { color:grey }
    .status-pass, .status-pass td { color:green }
    .status-fail, .status-fail td { color:red }
    .capitalize { text-transform:capitalize }
    <%block name="css"/>
    .content-wrap {<%block name="css_content_wrap"> margin:0 auto; padding:0 5px </%block>}
    <%block name="media_queries"/>
  </style>
</head>
<body<%block name="body_attr"/>>

  <div class="header">
    <div class="content-wrap">
      <a href="https://github.com/openstack/rally">Rally</a>&nbsp;
      <span><%block name="header_text"/></span>
    </div>
  </div>

  <div class="content-wrap">
    <%block name="content"/>
  </div>

  <script type="text/javascript"><%block name="js_after"/></script>
</body>
</html>
