## -*- coding: utf-8 -*-
<%inherit file="/base.mako"/>

<%block name="title_text">Rally Verification job results</%block>

<%block name="css">
    li { margin:2px 0 }
    a, a:visited { color:#039 }
    code { padding:0 15px; color:#888; display: block }
    .columns li { position:relative }
    .columns li > :first-child { display:block }
    .columns li > :nth-child(2) { display:block; position:static; left:165px; top:0; white-space:nowrap }
    .fail {color: red; text-transform: uppercase}
    .pass {color: green; display: none; text-transform: uppercase}
</%block>

<%block name="css_content_wrap">margin:0 auto; padding:0 5px</%block>

<%block name="media_queries">
    @media only screen and (min-width: 320px) { .content-wrap { width:400px } }
    @media only screen and (min-width: 520px) { .content-wrap { width:500px } }
    @media only screen and (min-width: 620px) { .content-wrap { width:90% } .columns li > :nth-child(2) { position:absolute } }
    @media only screen and (min-width: 720px) { .content-wrap { width:70% } }
</%block>

<%block name="header_text">Verify job results</%block>

<%block name="content">
    <h2>Job Logs and Job Result files</h2>
    <ul class="columns">
      <li><a href="console.html" class="rich">Job logs</a> <code>console.html</code>
      <li><a href="logs/">Logs of all services</a> <code>logs/</code>
      <li><a href="rally-verify/">Results files</a> <code>rally-verify/</code>
    </ul>

    <h2>Job Steps and Results</h2>
    <h3>Introduction</h3>
    <ul>
        <li>Install tempest</li>
        <li>Launch two verifications ("compute" set is used)</li>
        <li>List all verifications</li>
        <li>Compare two verification results</li>
    </ul>

    Each job step has output in all supported formats.

    <h3>Details</h3>
    <span class="${install}">[${install}]</span>
    <a href="rally-verify/tempest_installation.txt.gz">Tempest installation</a>
    <code>$ rally verify install</code>

    <span class="${genconfig}">[${genconfig}]</span>
    <a href="rally-verify/tempest_config_generation.txt.gz">Tempest config generation</a>
    <code>$ rally verify genconfig</code>

    <br>First verification run
    <ol>
        <li>
            <span class="${v1}">[${v1}]</span>
            <a href="rally-verify/1_verification_compute_set.txt.gz">Launch of verification</a>
            <code>$ rally verify start --set compute</code>
        </li>
        <li>
            <span class="${vr_1_html}">[${vr_1_html}]</span>
            <a href="rally-verify/1_verify_results_compute_set.html.gz">Display raw results in HTML</a>
            <code>$ rally verify results --html</code>
        </li>
        <li>
            <span class="${vr_1_json}">[${vr_1_json}]</span>
            <a href="rally-verify/1_verify_results_compute_set.json.gz">Display raw results in JSON</a>
            <code>$ rally verify results --json</code>
        </li>
        <li>
            <span class="${vs_1}">[${vs_1}]</span>
            <a href="rally-verify/1_verify_show_compute_set.txt.gz">Display results table of the verification</a>
            <code>$ rally verify show</code>
        </li>
        <li>
            <span class="${vsd_1}">[${vsd_1}]</span>
            <a href="rally-verify/1_verify_show_compute_set_detailed.txt.gz">Display results table of the verification with detailed errors</a><br />
            <code style="display: inline">$ rally verify show --detailed</code> or <code style="display: inline">$ rally verify detailed</code>
        </li>
    </ol>

    Second verification run
    <ol>
        <li>
            <span class="${v2}">[${v2}]</span>
            <a href="rally-verify/2_verification_compute_set.txt.gz">Launch of verification</a>
            <code>$ rally verify start --set compute</code>
        </li>
        <li>
            <span class="${vr_2_html}">[${vr_2_html}]</span>
            <a href="rally-verify/2_verify_results_compute_set.html.gz">Display results in HTML</a>
            <code>$ rally verify results --html</code>
        </li>
        <li>
            <span class="${vr_2_json}">[${vr_2_json}]</span>
            <a href="rally-verify/2_verify_results_compute_set.json.gz">Display results in JSON</a>
            <code>$ rally verify results --json</code>
        </li>
        <li>
            <span class="${vs_2}">[${vs_2}]</span>
            <a href="rally-verify/2_verify_show_compute_set.txt.gz">Display table results of the verification</a>
            <code>$ rally verify show</code>
        </li>
        <li>
            <span class="${vsd_2}">[${vsd_2}]</span>
            <a href="rally-verify/2_verify_show_compute_set_detailed.txt.gz">Display table results of the verification with detailed errors</a><br />
            <code style="display: inline">$ rally verify show --detailed</code> or <code style="display: inline">$ rally verify detailed</code>
        </li>
    </ol>

    <span class="${l}">[${l}]</span>
    <a href="rally-verify/verify_list.txt.gz">List of all verifications</a>
    <code>$ rally verify list</code>

    <span class="${c_html}">[${c_html}]</span>
    <a href="rally-verify/compare_results.html.gz">Compare two verification and display results in HTML</a>
    <code>$ rally verify compare --uuid-1 &lt;uuid-1&gt; --uuid-2 &lt;uuid-2&gt; --html</code>

    <span class="${c_json}">[${c_json}]</span>
    <a href="rally-verify/compare_results.json.gz">Compare two verifications and display results in JSON</a>
    <code>$ rally verify compare --uuid-1 &lt;uuid-1&gt; --uuid-2 &lt;uuid-2&gt; --json</code>

    <span class="${c_csv}">[${c_csv}]</span>
    <a href="rally-verify/compare_results.csv.gz">Compare two verifications and display results in CSV</a>
    <code>$ rally verify compare --uuid-1 &lt;uuid-1&gt; --uuid-2 &lt;uuid-2&gt; --csv</code>

    <h2>About Rally</h2>
    <p>Rally is benchmarking and verification system for OpenStack:</p>
    <ul>
      <li><a href="https://github.com/openstack/rally">Git repository</a>
      <li><a href="https://rally.readthedocs.org/en/latest/">Documentation</a>
      <li><a href="https://wiki.openstack.org/wiki/Rally/HowTo">How to use Rally (locally)</a>
      <li><a href="https://wiki.openstack.org/wiki/Rally/RallyGates">How to add Rally job to your project</a>
      <li><a href="https://www.mirantis.com/blog/rally-openstack-tempest-testing-made-simpler/">Rally: OpenStack Tempest Testing Made Simple(r) [a little outdated blog-post, but contains basic of Rally verification]</a>
    </ul>
</%block>
