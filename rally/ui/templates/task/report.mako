## -*- coding: utf-8 -*-
<%inherit file="/base.mako"/>

<%block name="html_attr"> ng-app="TaskApp"</%block>

<%block name="title_text">Rally Task Report</%block>

<%block name="libs">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.15-beta/nv.d3.min.css">
  <script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/angularjs/1.3.3/angular.min.js"></script>
  <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.4.13/d3.min.js"></script>
  <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.15-beta/nv.d3.min.js"></script>
</%block>

<%block name="js_before">
    "use strict";
    if (typeof angular === "object") { angular.module("TaskApp", []).controller(
      "TaskController", ["$scope", "$location", function($scope, $location) {

      $scope.location = {
        /* This is a junior brother of angular's $location, that allows non-`#'
           symbol in uri, like `#/path/hash' instead of `#/path#hash' */
        _splitter: "/",
        normalize: function(str) {
          /* Remove unwanted characters from string */
          if (typeof str !== "string") { return "" }
          return str.replace(/[^\w\-\.]/g, "")
        },
        _parseUri: function(uriStr) {
          /* :returns: {path:string, hash:string} */
          var self = this;
          var obj = {path: "", hash: ""};
          angular.forEach(uriStr.split(self._splitter), function(v){
            var s = self.normalize(v);
            if (! s) { return }
            if (! this.path) { this.path = s } else if (! this.hash) { this.hash = s }
          }, obj)
          return obj
        },
        uri: function(obj) {
          /* Getter/Setter */
          if (! obj) { return this._parseUri($location.url()) }
          if (obj.path && obj.hash) {
            $location.url(obj.path + this._splitter + obj.hash)
          } else if (obj.path) {
            $location.url(obj.path)
          } else {
            $location.url("/")
          }
        },
        path: function(path, hash) {
          /* Getter/Setter */
          var uri = this.uri();
          if (path === "") { return this.uri({}) }
          path = this.normalize(path);
          if (! path) { return uri.path }
          uri.path = path;
          var _hash = this.normalize(hash);
          if (_hash || hash === "") { uri.hash = _hash }
          return this.uri(uri)
        },
        hash: function(hash) {
          /* Getter/Setter */
          var uri = this.uri();
          if (! hash) { return uri.hash }
          return this.uri({path:uri.path, hash:hash})
        }
      }

      /* Dispatch */

      $scope.route = function(uri) {
        if (! ($scope.scenarios && $scope.scenarios.length)) {
          return
        }
        if (uri.path in $scope.scenarios_map) {
          $scope.view = {is_scenario:true};
          $scope.scenario = $scope.scenarios_map[uri.path];
          $scope.nav_idx = $scope.nav_map[uri.path];
          $scope.showTab(uri.hash);
        } else {
          $scope.scenario = null;
          if (uri.path === "source") {
            $scope.view = {is_source:true}
          } else {
            $scope.view = {is_main:true}
          }
        }
      }

      $scope.$on("$locationChangeSuccess", function (event, newUrl, oldUrl) {
        $scope.route($scope.location.uri())
      });

      /* Navigation */

      $scope.showNav  = function(nav_idx) {
        $scope.nav_idx = nav_idx
      }

      /* Tabs */

      $scope.tabs = [
        {
          id: "overview",
          name: "Overview",
          visible: function(){ return !! $scope.scenario.iterations.pie.length }
        },{
          id: "details",
          name: "Details",
          visible: function(){ return !! $scope.scenario.atomic.pie.length }
        },{
          id: "output",
          name: "Output",
          visible: function(){ return !! $scope.scenario.output.length }
        },{
          id: "failures",
          name: "Failures",
          visible: function(){ return !! $scope.scenario.errors.length }
        },{
          id: "task",
          name: "Input task",
          visible: function(){ return !! $scope.scenario.config }
        }
      ];
      $scope.tabs_map = {};
      angular.forEach($scope.tabs,
                      function(tab){ this[tab.id] = tab }, $scope.tabs_map);

      $scope.showTab = function(tab_id) {
        $scope.tab = tab_id in $scope.tabs_map ? tab_id : "overview"
      }

      for (var i in $scope.tabs) {
        if ($scope.tabs[i].id === $scope.location.hash()) {
          $scope.tab = $scope.tabs[i].id
        }
        $scope.tabs[i].isVisible = function(){
          if ($scope.scenario) {
            if (this.visible()) {
              return true
            }
            /* If tab should be hidden but is selected - show another one */
            if (this.id === $scope.location.hash()) {
              for (var i in $scope.tabs) {
                var tab = $scope.tabs[i];
                if (tab.id != this.id && tab.visible()) {
                  $scope.tab = tab.id;
                  return false
                }
              }
            }
          }
          return false
        }
      }

      /* Charts */

      var Charts = {
        _render: function(selector, data, chart){
          nv.addGraph(function() {
            d3.select(selector)
              .datum(data)
              .transition()
              .duration(0)
              .call(chart);
            nv.utils.windowResize(chart.update)
          })
        },
        pie: function(selector, data){
          var chart = nv.models.pieChart()
            .x(function(d) { return d.key })
            .y(function(d) { return d.values })
            .showLabels(true)
            .labelType("percent")
            .donut(true)
            .donutRatio(0.25)
            .donutLabelsOutside(true);
          var data_ = [];
          for (var i in data) {
            data_.push({key:data[i][0], values:data[i][1]})
          }
          this._render(selector, data_, chart)
        },
        stack: function(selector, data, conf){
          var chart = nv.models.stackedAreaChart()
            .x(function(d) { return d[0] })
            .y(function(d) { return d[1] })
            .clipEdge(true)
            .showControls(conf.controls)
            .useInteractiveGuideline(conf.guide);
          chart.xAxis
            .axisLabel(conf.xLabel || "")
            .showMaxMin(false)
            .tickFormat(d3.format(conf.xFormat || "d"));
          chart.yAxis
            .axisLabel(conf.yLabel || "")
            .tickFormat(d3.format(conf.yFormat || ",.3f"));
          var data_ = [];
          for (var i in data) {
            var d = {key:data[i][0], values:data[i][1]};
            if (d.key === "failed_duration") {
              d.color = "#f00"
            }
            data_.push(d)
          }
          this._render(selector, data_, chart)
        },
        histogram: function(selector, data){
          var chart = nv.models.multiBarChart()
            .reduceXTicks(true)
            .showControls(false)
            .transitionDuration(0)
            .groupSpacing(0.05);
          chart.legend
            .radioButtonMode(true)
          chart.xAxis
            .axisLabel("Duration (seconds)")
            .tickFormat(d3.format(",.2f"));
          chart.yAxis
            .axisLabel("Iterations (frequency)")
            .tickFormat(d3.format("d"));
          this._render(selector, data, chart)
        }
      };

      $scope.renderTotal = function() {
        if (! $scope.scenario) {
          return
        }

        Charts.stack(
          "#total-stack", $scope.scenario.iterations.iter,
          {xLabel: "Iteration sequence number",
           controls: true,
           guide: true});

        if ($scope.scenario.load_profile.length) {
           Charts.stack(
             "#load-profile-stack",
             $scope.scenario.load_profile,
             {xLabel: "Timeline (seconds)",
              xFormat: ",.2f", yFormat: "d"})
        }

        Charts.pie("#total-pie", $scope.scenario.iterations.pie);

        if ($scope.scenario.iterations.histogram.length) {
          var idx = this.totalHistogramModel.value;
          Charts.histogram("#total-histogram",
                           [$scope.scenario.iterations.histogram[idx]])
        }
      }

      $scope.renderDetails = function() {
        if (! $scope.scenario) {
          return
        }
         Charts.stack(
           "#atomic-stack",
           $scope.scenario.atomic.iter,
           {xLabel: "Iteration sequence number",
            controls: true,
            guide: true});
         if ($scope.scenario.atomic.pie) {
           Charts.pie("#atomic-pie", $scope.scenario.atomic.pie)
         }
        if ($scope.scenario.atomic.histogram.length) {
          var atomic = [];
          var idx = this.atomicHistogramModel.value;
          for (var i in $scope.scenario.atomic.histogram) {
            atomic[i] = $scope.scenario.atomic.histogram[i][idx]
          }
          Charts.histogram("#atomic-histogram", atomic)
        }
      }

      $scope.renderOutput = function() {
        if ($scope.scenario) {
          Charts.stack("#output-stack", $scope.scenario.output, {})
        }
      }

      $scope.showError = function(message) {
          return (function (e) {
            e.style.display = "block";
            e.textContent = message
          })(document.getElementById("page-error"))
      }

      /* Initialization */

      angular.element(document).ready(function(){
        $scope.source = ${source};
        $scope.scenarios = ${data};
        if (! $scope.scenarios.length) {
          return $scope.showError("No data...")
        }
        $scope.histogramOptions = [];
        $scope.totalHistogramModel = {label:'', value:0};
        $scope.atomicHistogramModel = {label:'', value:0};

        /* Compose data mapping */

        $scope.nav = [];
        $scope.nav_map = {};
        $scope.scenarios_map = {};
        var scenario_ref = $scope.location.path();
        var met = [];
        var itr = 0;
        var cls_idx = 0;
        var prev_cls, prev_met;

        for (var idx in $scope.scenarios) {
          var sc = $scope.scenarios[idx];
          if (! prev_cls) {
            prev_cls = sc.cls
          }
          else if (prev_cls !== sc.cls) {
            $scope.nav.push({cls:prev_cls, met:met, idx:cls_idx});
            prev_cls = sc.cls;
            met = [];
            itr = 1;
            cls_idx += 1
          }

          if (prev_met !== sc.met) {
            itr = 1
          }

          sc.ref = $scope.location.normalize(sc.cls+"."+sc.met+(itr > 1 ? "-"+itr : ""));
          $scope.scenarios_map[sc.ref] = sc;
          $scope.nav_map[sc.ref] = cls_idx;
          var current_ref = $scope.location.path();
          if (sc.ref === current_ref) {
            scenario_ref = sc.ref
          }

          met.push({name:sc.name, itr:itr, idx:idx, ref:sc.ref});
          prev_met = sc.met;
          itr += 1

          /* Compose histograms options, from first suitable scenario */

          if (! $scope.histogramOptions.length && sc.iterations.histogram) {
            for (var i in sc.iterations.histogram) {
              $scope.histogramOptions.push({
                label: sc.iterations.histogram[i].view,
                value: i
              })
            }
            $scope.totalHistogramModel = $scope.histogramOptions[0];
            $scope.atomicHistogramModel = $scope.histogramOptions[0];
          }
        }

        if (met.length) {
          $scope.nav.push({cls:prev_cls, met:met, idx:cls_idx})
        }

        /* Start */

        var uri = $scope.location.uri();
        uri.path = scenario_ref;
        $scope.route(uri);
        $scope.$digest()
      });
    }])}
</%block>

<%block name="css">
    .aside { margin:0 20px 0 0; display:block; width:255px; float:left }
    .aside > div { margin-bottom: 15px }
    .aside > div div:first-child { border-top-left-radius:4px; border-top-right-radius:4px }
    .aside > div div:last-child { border-bottom-left-radius:4px; border-bottom-right-radius:4px }
    .navcls { color:#678; background:#eee; border:1px solid #ddd; margin-bottom:-1px; display:block; padding:8px 9px; font-weight:bold; text-align:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer }
    .navcls.expanded { color:#469 }
    .navcls.active { background:#428bca; background-image:linear-gradient(to bottom, #428bca 0px, #3278b3 100%); border-color:#3278b3; color:#fff }
    .navmet { color:#555; background:#fff; border:1px solid #ddd; font-size:12px; display:block; margin-bottom:-1px; padding:8px 10px; text-align:left; text-overflow:ellipsis; white-space:nowrap; overflow:hidden; cursor:pointer }
    .navmet:hover { background:#f8f8f8 }
    .navmet.active, .navmet.active:hover { background:#428bca; background-image:linear-gradient(to bottom, #428bca 0px, #3278b3 100%); border-color:#3278b3; color:#fff }

    .tabs { list-style:outside none none; margin:0 0 5px; padding:0; border-bottom:1px solid #ddd }
    .tabs:after { clear:both }
    .tabs li { float:left; margin-bottom:-1px; display:block; position:relative }
    .tabs li div { border:1px solid transparent; border-radius:4px 4px 0 0; line-height:20px; margin-right:2px; padding:10px 15px; color:#428bca }
    .tabs li div:hover { border-color:#eee #eee #ddd; background:#eee; cursor:pointer; }
    .tabs li.active div { background:#fff; border-color:#ddd #ddd transparent; border-style:solid; border-width:1px; color:#555; cursor:default }
    .failure-mesg { color:#900 }
    .failure-trace { color:#333; white-space:pre; overflow:auto }

    .chart { height:300px }
    .chart .chart-dropdown { float:right; margin:0 35px 0 }
    .chart.lesser { padding:0; margin:0; float:left; width:40% }
    .chart.larger { padding:0; margin:0; float:left; width:59% }

    .expandable { cursor:pointer }
    .clearfix { clear:both }
    .top-margin { margin-top:40px !important }
    .sortable > .arrow { display:inline-block; width:12px; height:inherit; color:#c90 }
    .content-main { margin:0 5px; display:block; float:left }
</%block>

<%block name="media_queries">
    @media only screen and (min-width: 320px)  { .content-wrap { width:900px  } .content-main { width:600px } }
    @media only screen and (min-width: 900px)  { .content-wrap { width:880px  } .content-main { width:590px } }
    @media only screen and (min-width: 1000px) { .content-wrap { width:980px  } .content-main { width:690px } }
    @media only screen and (min-width: 1100px) { .content-wrap { width:1080px } .content-main { width:790px } }
    @media only screen and (min-width: 1200px) { .content-wrap { width:1180px } .content-main { width:890px } }
</%block>

<%block name="body_attr"> ng-controller="TaskController"</%block>

<%block name="header_text">task results</%block>

<%block name="content">
    <p id="page-error" class="notify-error" style="display:none"></p>

    <div id="content-nav" class="aside" ng-show="scenarios.length" ng-cloack>
      <div>
        <div class="navcls"
             ng-class="{active:view.is_main}"
             ng-click="location.path('')">Task overview</div>
        <div class="navcls"
             ng-class="{active:view.is_source}"
             ng-click="location.path('source', '')">Input file</div>
      </div>
      <div>
        <div class="navcls" title="{{n.cls}}"
             ng-repeat-start="n in nav track by $index"
             ng-click="showNav(n.idx)"
             ng-class="{expanded:n.idx==nav_idx}">
                <span ng-hide="n.idx==nav_idx">&#9658;</span>
                <span ng-show="n.idx==nav_idx">&#9660;</span>
                {{n.cls}}</div>
        <div class="navmet" title="{{m.name}}"
             ng-show="n.idx==nav_idx"
             ng-class="{active:m.ref==scenario.ref}"
             ng-click="location.path(m.ref)"
             ng-repeat="m in n.met track by $index"
             ng-repeat-end>{{m.name}}</div>
      </div>
    </div>

    <div id="content-main" class="content-main" ng-show="scenarios.length" ng-cloak>

      <div ng-show="view.is_main">
        <h1>Task overview</h1>
        <table class="linked compact"
               ng-init="ov_srt='ref'; ov_dir=false">
          <thead>
            <tr>
              <th class="sortable"
                  title="Scenario name, with optional suffix of call number"
                  ng-click="ov_srt='ref'; ov_dir=!ov_dir">
                Scenario
                <span class="arrow">
                  <b ng-show="ov_srt=='ref' && !ov_dir">&#x25b4;</b>
                  <b ng-show="ov_srt=='ref' && ov_dir">&#x25be;</b>
                </span>
              <th class="sortable"
                  title="How long the scenario run, without context duration"
                  ng-click="ov_srt='load_duration'; ov_dir=!ov_dir">
                Load duration (s)
                <span class="arrow">
                  <b ng-show="ov_srt=='load_duration' && !ov_dir">&#x25b4;</b>
                  <b ng-show="ov_srt=='load_duration' && ov_dir">&#x25be;</b>
                </span>
              <th class="sortable"
                  title="Scenario duration plus context duration"
                  ng-click="ov_srt='full_duration'; ov_dir=!ov_dir">
                Full duration (s)
                <span class="arrow">
                  <b ng-show="ov_srt=='full_duration' && !ov_dir">&#x25b4;</b>
                  <b ng-show="ov_srt=='full_duration' && ov_dir">&#x25be;</b>
                </span>
              <th class="sortable"
                  title="Number of iterations"
                  ng-click="ov_srt='iterations_count'; ov_dir=!ov_dir">
                Iterations
                <span class="arrow">
                  <b ng-show="ov_srt=='iterations_count' && !ov_dir">&#x25b4;</b>
                  <b ng-show="ov_srt=='iterations_count' && ov_dir">&#x25be;</b>
                </span>
              <th class="sortable"
                  title="Scenario runner type"
                  ng-click="ov_srt='runner'; ov_dir=!ov_dir">
                Runner
                <span class="arrow">
                  <b ng-show="ov_srt=='runner' && !ov_dir">&#x25b4;</b>
                  <b ng-show="ov_srt=='runner' && ov_dir">&#x25be;</b>
                </span>
              <th class="sortable"
                  title="Number of errors occured"
                  ng-click="ov_srt='errors.length'; ov_dir=!ov_dir">
                Errors
                <span class="arrow">
                  <b ng-show="ov_srt=='errors.length' && !ov_dir">&#x25b4;</b>
                  <b ng-show="ov_srt=='errors.length' && ov_dir">&#x25be;</b>
                </span>
              <th class="sortable"
                  title="Whether SLA check is successful"
                  ng-click="ov_srt='sla_success'; ov_dir=!ov_dir">
                Success (SLA)
                <span class="arrow">
                  <b ng-show="ov_srt=='sla_success' && !ov_dir">&#x25b4;</b>
                  <b ng-show="ov_srt=='sla_success' && ov_dir">&#x25be;</b>
                </span>
            <tr>
          </thead>
          <tbody>
            <tr ng-repeat="sc in scenarios | orderBy:ov_srt:ov_dir"
                ng-click="location.path(sc.ref)">
              <td>{{sc.ref}}
              <td>{{sc.load_duration | number:3}}
              <td>{{sc.full_duration | number:3}}
              <td>{{sc.iterations_count}}
              <td>{{sc.runner}}
              <td>{{sc.errors.length}}
              <td>
                <span ng-show="sc.sla_success" class="status-pass">&#x2714;</span>
                <span ng-hide="sc.sla_success" class="status-fail">&#x2716;</span>
            <tr>
          </tbody>
        </table>
      </div>

      <div ng-show="view.is_source">
        <h1>Input file</h1>
        <pre class="code">{{source}}</pre>
      </div>

      <div ng-show="view.is_scenario">
        <h1>{{scenario.cls}}.<wbr>{{scenario.name}} ({{scenario.full_duration | number:3}}s)</h1>
        <ul class="tabs">
          <li ng-repeat="t in tabs"
              ng-show="t.isVisible()"
              ng-class="{active:t.id == tab}"
              ng-click="location.hash(t.id)">
            <div>{{t.name}}</div>
          </li>
          <div class="clearfix"></div>
        </ul>
        <div ng-include="tab"></div>

        <script type="text/ng-template" id="overview">
          {{renderTotal()}}

          <p class="thesis">
            Load duration: <b>{{scenario.load_duration | number:3}} s</b> &nbsp;
            Full duration: <b>{{scenario.full_duration | number:3}} s</b> &nbsp;
            Iterations: <b>{{scenario.iterations_count}}</b> &nbsp;
            Failures: <b>{{scenario.errors.length}}</b>
          </p>

          <div ng-show="scenario.sla.length">
            <h2>Service-level agreement</h2>
            <table class="striped">
              <thead>
                <tr>
                  <th>Criterion
                  <th>Detail
                  <th>Success
                <tr>
              </thead>
              <tbody>
                <tr class="rich"
                    ng-repeat="row in scenario.sla track by $index"
                    ng-class="{'status-fail':!row.success, 'status-pass':row.success}">
                  <td>{{row.criterion}}
                  <td>{{row.detail}}
                  <td class="capitalize">{{row.success}}
                <tr>
              </tbody>
            </table>
          </div>

          <h2>Total durations</h2>
          <table class="striped">
            <thead>
              <tr>
                <th ng-repeat="i in scenario.table.cols track by $index">{{i}}
              <tr>
            </thead>
            <tbody>
              <tr ng-class="{richcolor:$last}"
                  ng-repeat="row in scenario.table.rows track by $index">
                <td ng-repeat="i in row track by $index">{{i}}
              <tr>
            </tbody>
          </table>

          <div class="chart">
            <svg id="total-stack"></svg>
          </div>

          <h3>Load Profile</h3>
          <div class="chart" style="height:180px" ng-show="scenario.load_profile[0][1].length">
            <svg id="load-profile-stack"></svg>
          </div>

          <h3>Distribution</h3>
          <div class="chart lesser top-margin">
            <svg id="total-pie"></svg>
          </div>

          <div class="chart larger top-margin"
               ng-show="scenario.iterations.histogram.length">
            <svg id="total-histogram"></svg>
            <select class="chart-dropdown"
                    ng-model="totalHistogramModel"
                    ng-options="i.label for i in histogramOptions"></select>
          </div>
        </script>

        <script type="text/ng-template" id="details">
          {{renderDetails()}}

          <h2>Atomic Action Durations</h2>
          <div class="chart">
            <svg id="atomic-stack"></svg>
          </div>

          <h3>Distribution</h3>
          <div class="chart lesser top-margin">
            <svg id="atomic-pie"></svg>
          </div>

          <div class="chart larger top-margin"
               ng-show="scenario.atomic.histogram.length">
            <svg id="atomic-histogram"></svg>
            <select class="chart-dropdown"
                    ng-model="atomicHistogramModel"
                    ng-options="i.label for i in histogramOptions"></select>
          </div>
        </script>

        <script type="text/ng-template" id="output">
          {{renderOutput()}}

          <h2>Scenario output</h2>
          <div class="chart">
            <svg id="output-stack"></svg>
          </div>
        </script>

        <script type="text/ng-template" id="failures">
          <h2>Task failures (<ng-pluralize
            count="scenario.errors.length"
            when="{'1': '1 iteration', 'other': '{} iterations'}"></ng-pluralize> failed)
          </h2>
          <table class="striped">
            <thead>
              <tr>
                <th>
                <th>Iteration
                <th>Exception type
                <th>Exception message
              </tr>
            </thead>
            <tbody>
              <tr class="expandable"
                  ng-repeat-start="i in scenario.errors track by $index"
                  ng-click="i.expanded = ! i.expanded">
                <td>
                  <span ng-hide="i.expanded">&#9658;</span>
                  <span ng-show="i.expanded">&#9660;</span>
                <td>{{i.iteration}}
                <td>{{i.type}}
                <td class="failure-mesg">{{i.message}}
              </tr>
              <tr ng-show="i.expanded" ng-repeat-end>
                <td colspan="4" class="failure-trace">{{i.traceback}}
              </tr>
            </tbody>
          </table>
        </script>

        <script type="text/ng-template" id="task">
          <h2>Subtask Configuration</h2>
          <pre class="code">{{scenario.config}}</pre>
        </script>
      </div>

    </div>
    <div class="clearfix"></div>
</%block>

<%block name="js_after">
    if (! window.angular) {(function(f){
      f(document.getElementById("content-nav"), "none");
      f(document.getElementById("content-main"), "none");
      f(document.getElementById("page-error"), "block").textContent = "Failed to load AngularJS framework"
    })(function(e, s){e.style.display = s; return e})}
</%block>
