<html>
<head>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.13-beta/nv.d3.min.css"
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

    <style>
        #task_choser select {
            width: 700px;
        }
        #results svg{
          height: 350px;
          width: 650px;
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

        $(function(){

            $("#task_choser").change(function(){
                var d = DATA[parseInt($(this).find("option:selected").val())]

                $("#results")
                    .empty()
                    .append($("#template .results").clone())
                    .find(".results .config")
                        .html("<pre>" + JSON.stringify(d["config"], "", 4) + "</pre>")
                        .end()

                    draw_stacked("#results .total_time .stackedarea", function(){
                        return d["time"]["iter"]
                    })

                    draw_pie("#results .total_time .pie", function(){
                        return d["time"]["pie"]
                    })

                    draw_pie("#results .atomic .pie", function(){
                        return d["atomic"]["pie"]
                    })

                    draw_stacked("#results .atomic .stackedarea", function(){
                        return d["atomic"]["iter"]
                    })


                    $("#template").hide()
            }).change();
        });

    </script>

</head>
    <body>
        <div id="task_choser">
            Select benchmark task:
            <select>
            % for i, name in enumerate(tasks):
                <option value=${i}>${name}</option>
            % endfor
            </select>
        </div>

        <div id="results"> </div>

        <div id="template">
            <div class="results">
                <div class="config"> </div>
                <div class="total_time">
                  <svg class="stackedarea"></svg>
                  <svg class="pie"> </svg>
                </div>
                <div class="atomic">
                  <svg class="stackedarea"></svg>
                  <svg class="pie"> </svg>
                </div>
            </div>
        </div>

    </body>
</html>