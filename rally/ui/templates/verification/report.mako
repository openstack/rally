## -*- coding: utf-8 -*-
<%inherit file="/base.mako"/>

<%block name="title_text">Tempest report</%block>

<%block name="libs">
  <script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>
</%block>

<%block name="css">
    .test-details-row { display:none }
    .test-details { font-family:monospace; white-space:pre; overflow:auto }
    .test-expandable { cursor:pointer }
    .test-expandable:hover { background:#f3f3f3 }

    .nav { margin: 15px 0 }
    .nav span { padding:1px 15px; margin:0 2px 0 0; cursor:pointer; background:#f3f3f3;
                color:#666; font-size:11px; border:2px #ddd solid; border-radius:10px }
    .nav span.active { background:#cfe3ff; border-color:#ace; color:#369 }

    table td { padding:4px 8px; word-wrap:break-word; word-break:break-all }
    table.stat { width:auto; margin:0 0 15px }
</%block>

<%block name="css_content_wrap">
    margin:0 auto; padding:0 5px
</%block>

<%block name="media_queries">
    @media only screen and (min-width: 300px)  { .content-wrap { width:370px } .test-details { width:360px } }
    @media only screen and (min-width: 500px)  { .content-wrap { width:470px } .test-details { width:460px } }
    @media only screen and (min-width: 600px)  { .content-wrap { width:570px } .test-details { width:560px } }
    @media only screen and (min-width: 700px)  { .content-wrap { width:670px } .test-details { width:660px } }
    @media only screen and (min-width: 800px)  { .content-wrap { width:770px } .test-details { width:760px } }
    @media only screen and (min-width: 900px)  { .content-wrap { width:870px } .test-details { width:860px } }
    @media only screen and (min-width: 1000px) { .content-wrap { width:970px } .test-details { width:960px } }
    @media only screen and (min-width: 1200px) { .content-wrap { width:auto  } .test-details { width:94%   } }
</%block>

<%block name="header_text">tempest report</%block>

<%block name="content">
    <p id="page-error" class="notify-error" style="display:none">Failed to load jQuery</p>

    <table class="stat">
      <thead>
        <tr>
          <th>Total
          <th>Pass
          <th>Fail
          <th>Error
          <th>Skip
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>${report['total']}
          <td>${report['passed']}
          <td>${report['failed']}
          <td>${report['errors']}
          <td>${report['skipped']}
        </tr>
      </tbody>
    </table>

    <div class="nav">
      <span data-navselector=".test-row">ALL</span>
      <span data-navselector=".status-fail">FAILED</span>
      <span data-navselector=".status-skip">SKIPPED</span>
      <span data-navselector=".status-pass">PASSED</span>
    </div>

    <table id="tests">
      <thead>
        <tr>
          <th>Status
          <th>Time
          <th colspan="5">Test Group/Test case
        <tr>
      </thead>
      <tbody>
      % for test in report['tests']:
        <tr id="${test['id']}" class="test-row status-${test['status']}">
          <td>${test['status']}
          <td>${test['time']}
          <td colspan="5">${test['desc']}
        </tr>
        % if 'output' in test:
        <tr class="test-details-row">
          <td colspan="6"><div class="test-details">${test['output'] | h}</div>
        </tr>
        % endif
      % endfor
      </tbody>
    </table>
</%block>

<%block name="js_after">
    if (typeof $ === "undefined") {
      /* If jQuery loading has failed */
      document.getElementById("page-error").style.display = "block"
    } else {
      $(function(){
        $(".test-details-row")
          .prev()
          .addClass("test-expandable")
          .click( function(){ $(this).next().toggle() });

        (function($navs) {
          $navs.click(function(){
              var $this = $(this);
              $navs.removeClass("active").filter($this).addClass("active");
              $("#tests tbody tr").hide().filter($this.attr("data-navselector")).show()
            }).first().click()
        }($(".nav [data-navselector]")));
      })
    }
</%block>
