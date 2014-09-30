<!DOCTYPE html>
<html ng-app="BenchmarkApp">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rally | Benchmark Task Report</title>
  <link rel="stylesheet" href="http://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.13-beta/nv.d3.min.css">
  <link rel="stylesheet" href="http://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.2.0/css/bootstrap.min.css">
  <link rel="stylesheet" href="http://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.2.0/css/bootstrap-theme.min.css">
  <script src="http://cdnjs.cloudflare.com/ajax/libs/angular.js/1.2.20/angular.min.js"></script>
  <script src="http://cdnjs.cloudflare.com/ajax/libs/d3/3.4.1/d3.min.js"></script>
  <script src="http://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.13-beta/nv.d3.min.js"></script>
  <script>
    app = angular.module("BenchmarkApp", []);
    app.controller("ScenarioCtl", ["$scope", function($scope) {

      /* Navigation */

      $scope.showNav = function(class_idx) {
        $scope.class_idx = class_idx
      }

      /* Tabs */

      $scope.tabs = [
        {
          id: "overview.html",
          name: "Overview",
          visible: function(){ return !! $scope.scenario.duration.pie.length }
        },{
          id: "details.html",
          name: "Details",
          visible: function(){ return !! $scope.scenario.atomic.pie.length }
        },{
          id: "config.html",
          name: "Config",
          visible: function(){ return !! $scope.scenario.config }
        }
      ];

      for (var i in $scope.tabs) {
        $scope.tabs[i].showContent = function(){
          $scope.tabId = this.id
        }
        $scope.tabs[i].isVisible = function(){
          if ($scope.scenario) {
            if (this.visible()) {
              return true
            }
            /* If tab should be hidden but is selected - show another one */
            if ($scope.tabId == this.id) {
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

      $scope.tabId = "overview.html";

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
            .margin({left: 75})
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
            .margin({left: 75})
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

      $scope.renderAtomic = function() {
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

      $scope.showScenario = function(class_idx, scenario_idx) {
        $scope.class_idx = class_idx;
        $scope.scenario_idx = scenario_idx;
        $scope.scenario = $scope.scenarios[scenario_idx]
      }

      /* Initialization */

      angular.element(document).ready(function () {
        $scope.scenarios = ${data};

        $scope.histogramOptions = [];
        $scope.totalHistogramModel = {label:'', value:0};
        $scope.atomicHistogramModel = {label:'', value:0};

        /* Compose nav data */

        $scope.nav = [];
        var class_idx = 0;
        var scenario_idx = 0;
        var met = [];
        var itr = 0;
        var cls_idx = 0;
        var prev_cls, prev_met, ref;

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

          ref = "#/"+prev_cls+"."+sc.met+(itr > 1 ? "-"+itr : "");
          if (ref === window.location.hash) {
            scenario_idx = idx;
            class_idx = cls_idx;
          }

          met.push({name:sc.name, itr:itr, idx:idx, ref:ref});
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

        $scope.showScenario(class_idx, scenario_idx);
        $scope.$digest()
      });

    }])
  </script>
  <style>
    body {
      margin-bottom: 40px;
    }
    .list-group-item.scenario-class,
    .list-group-item.scenario-class:visited,
    .list-group-item.scenario-class:active,
    .list-group-item.scenario-class:focus,
    .list-group-item.scenario-class:hover {
      background: #eee;
      color: #469;
      font-weight: bold;
    }
    .list-group-item.scenario-method {
      font-size: 12px;
    }
    .chart-container {
      height: 300px;
      margin-bottom: 20px;
    }
    .chart-container.topmargin {
      margin-top: 40px;
    }
    .chart-container .chart-dropdown {
      float: right;
      margin: 0 35px 0;
    }
    h1 {
      color: #666;
      margin: 0 0 25px;
    }
    h2 {
      margin: 30px 0 15px;
      color: #666;
    }
    a:focus {
      outline:none;
    }
  </style>
</head>
<body>

  <div role="navigation" class="navbar navbar-inverse">
    <div class="container">
      <div class="navbar-header">
        <a href="https://github.com/stackforge/rally" class="navbar-brand" style="margin-left:0">Rally</a>
        <span class="navbar-brand" style="color:#fff">benchmark results</span>
      </div>
    </div>
  </div>

  <div class="container" ng-controller="ScenarioCtl">

    <h3 ng-hide="scenario" class="alert alert-danger">Failed to render scenario data</h3>

    <div class="col-md-3" ng-show="scenario">
      <div class="list-group">
        <span data-scenarios-class ng-repeat="n in nav track by $index">
          <a class="list-group-item scenario-class"
             href="javascript:;"
             ng-click="showNav(n.idx)">{{n.cls}}</a>
          <a class="list-group-item scenario-method"
             href="{{m.ref}}"
             ng-show="n.idx == class_idx"
             ng-class="{active:m.idx == scenario_idx}"
             ng-click="showScenario(n.idx, m.idx)"
             ng-repeat="m in n.met track by $index">{{m.name}}</a>
        </span>
      </div>
    </div>

    <div class="col-md-9" ng-show="scenario">

        <h1>{{scenario.cls}}.<wbr>{{scenario.name}}</h1>
        <ul role="tablist" class="nav nav-tabs">
          <li ng-repeat="tab in tabs"
              ng-class="{active:tab.id == tabId}"
              ng-click="tab.showContent()"
              ng-show="tab.isVisible()">
            <a href="javascript:;">{{tab.name}}</a>
          </li>
        </ul>
        <div ng-include="tabId"></div>

        <script type="text/ng-template" id="overview.html">
          <h2>Table for task results</h2>
          <table class="table table-striped">
            <thead>
              <tr>
                <th ng-repeat="col in scenario.table_cols track by $index">{{col.title}}</th>
              <tr>
            </thead>
            <tbody>
              <tr ng-repeat="row in scenario.table_rows track by $index">
                <td ng-repeat="i in row track by $index">{{i}}</td>
              <tr>
            </tbody>
          </table>

          {{renderTotal()}}
          <h2>Charts for the Total Duration</h2>
          <div class="chart-container">
            <svg id="total-stack"></svg>
          </div>

          <div class="col-md-5 chart-container topmargin">
            <svg id="total-pie"></svg>
          </div>

          <div class="col-md-7 chart-container topmargin" ng-show="scenario.duration.histogram">
            <svg id="total-histogram"></svg>
            <select class="chart-dropdown"
                    ng-model="totalHistogramModel"
                    ng-options="i.label for i in histogramOptions"></select>
          </div>
        </script>

        <script type="text/ng-template" id="details.html">
          {{renderAtomic()}}
          <h2>Charts for every Atomic Action</h2>
          <div class="chart-container">
            <svg id="atomic-stack"></svg>
          </div>

          <div class="col-md-5 chart-container topmargin">
            <svg id="atomic-pie"></svg>
          </div>

          <div class="col-md-7 chart-container topmargin textcenter" ng-show="scenario.atomic.histogram">
            <svg id="atomic-histogram"></svg>
            <select class="chart-dropdown"
                    ng-model="atomicHistogramModel"
                    ng-options="i.label for i in histogramOptions"></select>
          </div>
        </script>

        <script type="text/ng-template" id="config.html">
          <h2>Scenario Configuration</h2>
          <pre>{{scenario.config}}</pre>
        </script>

      </div>

  </div>

</body>
</html>
