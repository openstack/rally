<!DOCTYPE html>
<html ng-app="BenchmarkApp">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rally | Benchmark Task Report</title>
  <link rel="stylesheet" href="http://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.15-beta/nv.d3.min.css">
  <script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/angularjs/1.3.0-rc.5/angular.min.js"></script>
  <script type="text/javascript" src="http://cdnjs.cloudflare.com/ajax/libs/d3/3.4.12/d3.min.js"></script>
  <script type="text/javascript" src="http://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.15-beta/nv.d3.min.js"></script>
  <script type="text/javascript">
    app = angular.module("BenchmarkApp", []);
    app.controller("BenchmarkController", ["$scope", "$location", function($scope, $location) {

      /* Navigation */

      $scope.showNav = function(nav_idx) {
        $scope.nav_idx = nav_idx
      }

      /* Tabs */

      $scope.tabs = [
        {
          id: "overview",
          name: "Overview",
          visible: function(){ return !! $scope.scenario.duration.pie.length }
        },{
          id: "details",
          name: "Details",
          visible: function(){ return !! $scope.scenario.atomic.pie.length }
        },{
          id: "config",
          name: "Config",
          visible: function(){ return !! $scope.scenario.config }
        }
      ];

      $scope.tabId = "overview";

      for (var i in $scope.tabs) {
        if ($scope.tabs[i].id === $location.hash()) {
          $scope.tabId = $scope.tabs[i].id
        }
        $scope.tabs[i].showContent = function(){
          $location.hash(this.id);
          $scope.tabId = this.id
        }
        $scope.tabs[i].isVisible = function(){
          if ($scope.scenario) {
            if (this.visible()) {
              return true
            }
            /* If tab should be hidden but is selected - show another one */
            if (this.id === $location.hash()) {
              for (var i in $scope.tabs) {
                var tab = $scope.tabs[i];
                if (tab.id != this.id && tab.visible()) {
                  tab.showContent();
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
        _render: function(selector, datum, chart){
          nv.addGraph(function() {
            d3.select(selector)
              .datum(datum)
              .transition()
              .duration(0)
              .call(chart);
            nv.utils.windowResize(chart.update)
          })
        },
        pie: function(selector, datum){
          var chart = nv.models.pieChart()
            .x(function(d) { return d.key })
            .y(function(d) { return d.value })
            .showLabels(true)
            .labelType("percent")
            .donut(true)
            .donutRatio(0.25)
            .donutLabelsOutside(true);
            this._render(selector, datum, chart)
        },
        stack: function(selector, datum){
          var chart = nv.models.stackedAreaChart()
            .x(function(d) { return d[0] })
            .y(function(d) { return d[1] })
            .useInteractiveGuideline(true)
            .clipEdge(true);
          chart.xAxis
            .axisLabel("Iteration (order number of method's call)")
            .showMaxMin(false)
            .tickFormat(d3.format('d'));
          chart.yAxis
            .axisLabel("Duration (seconds)")
            .tickFormat(d3.format(',.2f'));
          this._render(selector, datum, chart)
        },
        histogram: function(selector, datum){
          var chart = nv.models.multiBarChart()
            .reduceXTicks(true)
            .showControls(false)
            .groupSpacing(0.05);
          chart.legend
            .radioButtonMode(true)
          chart.xAxis
            .axisLabel("Duration (seconds)")
            .tickFormat(d3.format(',.2f'));
          chart.yAxis
            .axisLabel("Iterations (frequency)")
            .tickFormat(d3.format('d'));
          this._render(selector, datum, chart)
        }
      };

      $scope.renderTotal = function() {
        if (! $scope.scenario) {
          return
        }
        Charts.stack("#total-stack", $scope.scenario.duration.iter);
        Charts.pie("#total-pie", $scope.scenario.duration.pie);

        if ($scope.scenario.duration.histogram.length) {
          var idx = this.totalHistogramModel.value;
          Charts.histogram("#total-histogram",
                           [$scope.scenario.duration.histogram[idx]])
        }
      }

      $scope.renderDetails = function() {
        if (! $scope.scenario) {
          return
        }
        Charts.stack("#atomic-stack", $scope.scenario.atomic.iter);
        Charts.pie("#atomic-pie", $scope.scenario.atomic.pie);
        if ($scope.scenario.atomic.histogram.length) {
          var atomic = [];
          var idx = this.atomicHistogramModel.value;
          for (var i in $scope.scenario.atomic.histogram) {
            atomic[i] = $scope.scenario.atomic.histogram[i][idx]
          }
          Charts.histogram("#atomic-histogram", atomic)
        }
      }

      /* Scenario */

      $scope.showScenario = function(nav_idx, scenario_idx) {
        $scope.nav_idx = nav_idx;
        $scope.scenario_idx = scenario_idx;
        $scope.scenario = $scope.scenarios[scenario_idx];
        $location.path($scope.scenario.ref);
      }

      /* Initialization */

      angular.element(document).ready(function () {
        $scope.scenarios = ${data};

        $scope.histogramOptions = [];
        $scope.totalHistogramModel = {label:'', value:0};
        $scope.atomicHistogramModel = {label:'', value:0};

        /* Compose nav data */

        $scope.nav = [];
        var nav_idx = 0;
        var scenario_idx = 0;
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

          sc.ref = "/"+prev_cls+"."+sc.met+(itr > 1 ? "-"+itr : "");
          if (sc.ref === $location.path()) {
            scenario_idx = idx;
            nav_idx = cls_idx;
          }

          met.push({name:sc.name, itr:itr, idx:idx});
          prev_met = sc.met;
          itr += 1

          /* Compose histograms options, from first suitable scenario */

          if (! $scope.histogramOptions.length && sc.duration.histogram) {
            for (var i in sc.duration.histogram) {
              $scope.histogramOptions.push({
                label: sc.duration.histogram[i].method,
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

        $scope.showScenario(nav_idx, scenario_idx);
        $scope.$digest()
      });
    }])
  </script>
  <style>
    body { margin:0 0 50px; padding:0; font-size:14px; font-family:Helvetica,Arial,sans-serif }
    a, a:active, a:focus, a:visited { text-decoration: none; outline:none }
    h1 { color:#666; margin:0 0 25px; font-size:32px; font-weight:normal }
    h2 { color:#666; margin:30px 0 15px; font-size:26px; font-weight:normal }
    pre { padding:10px; font-size:13px; color:#333; background:#f5f5f5; border:1px solid #ccc; border-radius:4px }
    table { border-collapse:collapse; border-spacing:0; width:100%; font-size:12px }
    table th { text-align:left; padding:8px; color:#000; border:2px solid #ddd; border-width:0 0 2px 0 }
    table td { text-align:left; border-top:1px solid #ddd; padding:8px; color:#333 }
    table.striped tr:nth-child(odd) td { background:#f9f9f9 }
    table .highlight td { color:#036; font-weight:bold }

    .header { text-align:left; background:#333; font-size:18px; padding:13px 6px; margin-bottom: 20px; color:#fff; background-image: linear-gradient(to bottom, #444 0px, #222 100%) }
    .header a, .header a:visited, .header a:focus { color:#999 }

    .aside { margin:0 20px 0 0; display:block; width:255px; float:left }
    .aside div:first-child { border-radius:4px 4px 0 0 }
    .aside div:last-child { border-radius:0 0 4px 4px }
    .nav-group { color:#678; background:#eee; border:1px solid #ddd; margin-bottom:-1px; display:block; padding:8px 9px; font-weight:bold; text-aligh:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer }
    .nav-group.active { color:#469 }
    .nav-item { color:#555; background:#fff; border:1px solid #ddd; font-size: 12px; display:block; margin-bottom:-1px; padding:8px 10px; text-aligh:left; text-overflow:ellipsis; white-space:nowrap; overflow:hidden; cursor:pointer }
    .nav-item:hover { background:#f8f8f8 }
    .nav-item.active, .nav-item.active:hover { background:#428bca; background-image: linear-gradient(to bottom, #428bca 0px, #3278b3 100%); border-color:#3278b3; color:#fff }

    .tabs { list-style:outside none none; margin-bottom:0; padding-left:0; border-bottom:1px solid #ddd }
    .tabs:after { clear:both }
    .tabs li { float:left; margin-bottom:-1px; display:block; position:relative }
    .tabs li div { border:1px solid transparent; border-radius:4px 4px 0 0; line-height:20px; margin-right:2px; padding:10px 15px; color:#428bca }
    .tabs li div:hover { border-color:#eee #eee #ddd; background:#eee; cursor:pointer; }
    .tabs li.active div { background:#fff; border-color: #ddd #ddd transparent; border-style: solid; border-width: 1px; color:#555; cursor:default }

    .chart { height:300px }
    .chart .chart-dropdown { float:right; margin:0 35px 0 }
    .chart.lesser { padding:0; margin:0; float:left; width:40% }
    .chart.larger { padding:0; margin:0; float:left; width:59% }

    .content-wrap { margin:0 auto; padding:0 5px }
    .content-main { margin:0 5px; display:block; float:left }

    .clearfix { clear:both }
    .text-error { color:red }
    .top-margin { margin-top:40px !important }

    @media only screen and (min-width: 320px)  { .content-wrap { width:900px  } .content-main { width:600px } }
    @media only screen and (min-width: 900px)  { .content-wrap { width:880px  } .content-main { width:590px } }
    @media only screen and (min-width: 1000px) { .content-wrap { width:980px  } .content-main { width:690px } }
    @media only screen and (min-width: 1100px) { .content-wrap { width:1080px } .content-main { width:790px } }
    @media only screen and (min-width: 1200px) { .content-wrap { width:1180px } .content-main { width:890px } }
  </style>
</head>
<body>

  <div class="header">
    <div class="content-wrap">
      <a href="https://github.com/stackforge/rally">Rally</a>&nbsp;
      <span>benchmark results</span>
    </div>
  </div>

  <div class="content-wrap" ng-controller="BenchmarkController">

    <div ng-hide="scenario" class="text-error">Failed to render scenario data</div>

    <div class="aside" ng-show="scenario">
      <div class="nav-group" title="{{n.cls}}"
           ng-repeat-start="n in nav track by $index"
           ng-click="showNav(n.idx)"
           ng-class="{active:n.idx == nav_idx}">
              <span ng-hide="n.idx == nav_idx">&#9658;</span>
              <span ng-show="n.idx == nav_idx">&#9660;</span>
              {{n.cls}}
      </div>
      <div class="nav-item" title="{{m.name}}"
           ng-show="n.idx == nav_idx"
           ng-class="{active:m.idx == scenario_idx}"
           ng-click="showScenario(n.idx, m.idx)"
           ng-repeat="m in n.met track by $index"
           ng-repeat-end>{{m.name}}</div>
    </div>

    <div class="content-main" ng-show="scenario">

      <h1>{{scenario.cls}}.<wbr>{{scenario.name}}</h1>
      <ul class="tabs">
        <li ng-repeat="tab in tabs"
            ng-class="{active:tab.id == tabId}"
            ng-click="tab.showContent()"
            ng-show="tab.isVisible()">
          <div>{{tab.name}}</div>
        </li>
        <div class="clearfix"></div>
      </ul>
      <div ng-include="tabId"></div>

      <script type="text/ng-template" id="overview">
        {{renderTotal()}}

        <h2>Table for task results</h2>
        <table class="striped lastrow">
          <thead>
            <tr>
              <th ng-repeat="i in scenario.table_cols track by $index">{{i}}</th>
            <tr>
          </thead>
          <tbody>
            <tr ng-class="{highlight:$last}" ng-repeat="row in scenario.table_rows track by $index">
              <td ng-repeat="i in row track by $index">{{i}}</td>
            <tr>
          </tbody>
        </table>

        <h2>Charts for the Total Duration</h2>
        <div class="chart">
          <svg id="total-stack"></svg>
        </div>

        <div class="chart lesser top-margin">
          <svg id="total-pie"></svg>
        </div>

        <div class="chart larger top-margin"
             ng-show="scenario.duration.histogram.length">
          <svg id="total-histogram"></svg>
          <select class="chart-dropdown"
                  ng-model="totalHistogramModel"
                  ng-options="i.label for i in histogramOptions"></select>
        </div>
      </script>

      <script type="text/ng-template" id="details">
        {{renderDetails()}}

        <h2>Charts for every Atomic Action</h2>
        <div class="chart">
          <svg id="atomic-stack"></svg>
        </div>

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

      <script type="text/ng-template" id="config">
        <h2>Scenario Configuration</h2>
        <pre>{{scenario.config}}</pre>
      </script>

    </div>
    <div class="clearfix"></div>

  </div>

</body>
</html>
