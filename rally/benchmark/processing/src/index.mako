<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Rally | Benchmark Task Report</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.13-beta/nv.d3.min.css"
          rel="stylesheet"
          type="text/css" />
    <link href="https://cdn.datatables.net/1.10.0/css/jquery.dataTables.css"
          rel="stylesheet"
          type="text/css" />

    <!-- Remove jQuery and use d3.select in futuer -->
    <script type="text/javascript"
            src="https://cdnjs.cloudflare.com/ajax/libs/jquery/2.1.0/jquery.min.js"
            charset="utf-8">
    </script>
    <script type="text/javascript"
            src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.4.1/d3.min.js"
            charset="utf-8">
    </script>
    <script type="text/javascript"
            src="https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.13-beta/nv.d3.min.js"
            charset="utf-8">
    </script>
    <script type="text/javascript"
            src="https://cdn.datatables.net/1.10.0/js/jquery.dataTables.js"
            charset="utf-8">
    </script>

    <style>
        #task_choser select {
            width: 700px;
        }
        #results svg{
          height: 350px;
          width: 650px;
          float: left;
        }
        #results select{
            float: left;
        }
        #results svg.pie{
            width: 350px;
        }
        div.atomic {
            clear: both;
        }
        #results {
            min-width: 1000px;
            overflow: scroll;
        }
        #atomic_table {
            padding-bottom:0px;
        }.dataTables_wrapper {width: 950px;}
    </style>


    <script>
        var DATA = ${data}

        function draw_stacked(where, source){
            nv.addGraph(function() {
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

                d3.select(where)
                    .datum(source)
                    .transition().duration(500).call(chart);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        }


        function draw_pie(where, source){
            nv.addGraph(function() {
                var chart = nv.models.pieChart()
                    .x(function(d) { return d.key })
                    .y(function(d) { return d.value })
                    .showLabels(true)
                    .labelType("percent")
                    .labelThreshold(.05)
                    .donut(true);

                d3.select(where)
                    .datum(source)
                    .transition().duration(1200)
                    .call(chart);

                return chart;
            });
        }


        function draw_histogram(where, source){
            nv.addGraph(function() {
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

                d3.select(where)
                    .datum(source)
                    .call(chart);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        }

        $(function(){

            $("#task_choser").change(function(){
                var d = DATA[parseInt($(this).find("option:selected").val())]

                $("#results")
                    .empty()
                    .append($("#template .results").clone())
                    .find(".results .config")
                        .html("<pre>" + JSON.stringify(d["config"], "", 4) + "</pre>")
                        .end()

                // Find
                var total_histogram_select = $("#results > .results > .total_duration > .histogram_select");
                var atomic_histogram_select = $("#results > .results > .atomic > .histogram_select");
                // Populate
                for (var i = 0; i < d.duration.histogram.length; i++) {
                    var option = document.createElement('option');
                    option.text = d.duration.histogram[i].method;
                    total_histogram_select.get(0).add(option);
                    atomic_histogram_select.get(0).add(option.cloneNode(true));
                }
                // Bind onchange event
                total_histogram_select.change(function(){
                    var i = total_histogram_select.get(0).selectedIndex;
                    $("#results > .results > .total_duration > .histogram").empty();
                    draw_histogram("#results .total_duration .histogram", function(){
                        return [d["duration"]["histogram"][i]];
                    });
                });
                atomic_histogram_select.change(function(){
                    $("#results > .results > .atomic > .histogram").empty();
                    draw_histogram("#results .atomic .histogram", function(){
                        var atomic_actions = []
                        var selected = atomic_histogram_select.get(0).selectedIndex;
                        for (var i = 0; i < d.atomic.histogram.length; i++) {
                            atomic_actions[i] = d["atomic"]["histogram"][i][selected];
                        }
                        return atomic_actions;
                    });
                });

                $('#atomic_table').dataTable({
                    "data": d["table_rows"],
                    "columns": d["table_cols"],
                    "searching": false,
                    "paging": false
                });

                draw_stacked("#results .total_duration .stackedarea", function(){
                    return d["duration"]["iter"]
                })

                draw_pie("#results .total_duration .pie", function(){
                    return d["duration"]["pie"]
                })

                if (d["duration"]["histogram"].length > 0) {
                  //at least one successfull iteration so plot histogram
                  draw_histogram("#results .total_duration .histogram", function(){
                      return [d["duration"]["histogram"][0]];
                  })
                } else {
                  total_histogram_select.hide()
                }


                if (d["atomic"]["iter"].length > 0){
                // There are atomic actions results to plot
                  draw_pie("#results .atomic .pie", function(){
                      return d["atomic"]["pie"]
                  })

                  draw_stacked("#results .atomic .stackedarea", function(){
                      return d["atomic"]["iter"]
                  })

                  draw_histogram("#results .atomic .histogram", function(){
                      var atomic_actions = []
                      for (var i = 0; i < d.atomic.histogram.length; i++) {
                          atomic_actions[i] = d["atomic"]["histogram"][i][0];
                      }
                      return atomic_actions;
                  })
                } else {
                  // No atomic actions results
                  // Don't show atomic actions header & Select
                  $("#results .atomic").hide()
                }

                $("#template").hide()
            }).change();
        });

    </script>

</head>
    <body>
        <div id="task_choser">
            <h2>Select benchmark scenario:</h2>
            <select>
            % for i, name in enumerate(tasks):
                <option value=${i}>${name}</option>
            % endfor
            </select>
        </div>

        <div id="results"> </div>

        <div id="template">
            <div class="results">
                <h2>Benchmark Scenario Configuration</h2>
                <div class="config"></div>
                <h2>Table for task results</h2>
                <table cellpadding="0" cellspacing="0" border="0" class="display" id="atomic_table"></table>
                <h2>Charts for the Total Duration</h2>
                <div class="total_duration">
                    <svg class="stackedarea"></svg>
                    <svg class="pie"></svg>
                    <svg class="histogram"></svg>
                    <select class="histogram_select"></select>
                </div>
                <div class="atomic">
                    <h2>Charts for every Atomic Action</h2>
                    <svg class="stackedarea"></svg>
                    <svg class="pie"> </svg>
                    <svg class="histogram"></svg>
                    <select class="histogram_select"></select>
                </div>
            </div>
        </div>
    </body>
</html>
