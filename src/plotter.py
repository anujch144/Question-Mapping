import numpy as np
import pandas as pd
import logging

import plotly.express as px
import plotly.io as pio
import plotly.offline as ofl
import plotly.graph_objects as go
import plotly.colors as pc


class PlotlyPlotter:

    defaultTemplate = None
    defaultFont = None
    defaultColors = None
    logger = None

    def __init__(self, plotterConfig):
        self.logger = logging.getLogger(__name__)

        self.defaultTemplate = plotterConfig["template"]
        self.defaultFont = {
            "fontFamily": plotterConfig["fontFamily"],
            "fontSize": plotterConfig["fontSize"],
            "fontColor": plotterConfig["fontColor"],
        }
        self.defaultColors = {
            "white": "#ffffff",
            "black": "#000000",
            "darkGray": "#333333",
            "lightGray": "#888888",
            "transparent": "rgba(0, 0, 0, 0)",
        }
        self.defaultColorScale = px.colors.sequential.Blues

    def setPlotProperties(
        self,
        fig: object,
        figSize: tuple = None,
        fontSize: int = None,
        fontColor: str = None,
        colorScale: object = None,
        showXAxis: bool = False,
        showYAxis: bool = False,
        xAxisRange: tuple = None,
        yAxisRange: tuple = None,
        xAxisTitle: str = None,
        yAxisTitle: str = None,
        showTickLabels: bool = False,
        showGrid: bool = False,
        showLegend: bool = False,
        plotMargin: int = 60,
        hoverTemplate: str = None,
        hideTraceName: bool = True,
    ) -> object:

        fig.update_layout(template=self.defaultTemplate)
        if colorScale is None:
            colorScale = self.defaultColorScale
        fig.update_layout(colorway=colorScale)

        if fontSize is None:
            fontSize = self.defaultFont["fontSize"]
        if fontColor is None:
            fontColor = self.defaultFont["fontColor"]
        fig.update_layout(
            font_family=self.defaultFont["fontFamily"],
            font_color=fontColor,
            font_size=fontSize,
        )
        if figSize is not None:
            fig.update_layout(
                autosize=False,
                width=figSize[0],
                height=figSize[1],
            )

        fig.update_layout(showlegend=showLegend)
        fig.update_layout(
            margin=dict(l=plotMargin, r=plotMargin, t=plotMargin, b=plotMargin)
        )
        fig.update_layout(paper_bgcolor=self.defaultColors["white"])

        # Hover label
        if (
            (fig.data is not None)
            and (len(fig.data) > 0)
            and ("hoverinfo" in fig.data[0])
        ):
            if hoverTemplate is None:
                fig.update_traces(hoverinfo="skip")
            else:
                hoverTemplate += "<extra></extra>"
                fig.update_traces(hovertemplate=hoverTemplate)
                fig.update_layout(
                    hoverlabel=dict(
                        bgcolor=self.defaultColors["white"],
                        bordercolor=self.defaultFont["fontColor"],
                        font_size=(fontSize - 4),
                        font_family=self.defaultFont["fontFamily"],
                        font_color=self.defaultFont["fontColor"],
                    )
                )

        # X, Y axes
        axisDict = dict(
            rangemode="tozero",
            ticks="outside",
            ticklen=5,
            tickcolor=self.defaultColors["white"],
            showticklabels=showTickLabels,
            zerolinewidth=2,
            zerolinecolor=self.defaultFont["fontColor"],
            showgrid=showGrid,
        )
        xAxisDict = axisDict.copy()
        xAxisDict["zeroline"] = showYAxis
        if xAxisRange is not None:
            xAxisDict["range"] = xAxisRange
        if xAxisTitle is not None:
            xAxisDict["title"] = xAxisTitle

        yAxisDict = axisDict.copy()
        yAxisDict["zeroline"] = showXAxis
        if yAxisRange is not None:
            yAxisDict["range"] = yAxisRange
        if yAxisTitle is not None:
            yAxisDict["title"] = yAxisTitle

        fig.update_xaxes(xAxisDict)
        fig.update_yaxes(yAxisDict)

        return fig

    # -------------------------------------------------------- Basic Plots -------------------------------------------------------- #

    def scatterPlot(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        plotTitle: str = None,
        plotMode: str = "markers",
        smoothing: float = 1,
        figSize: tuple = None,
    ) -> None:
        trace = go.Scatter(
            x=data[x],
            y=data[y],
            mode=plotMode,
            name=f"{x}-{y} Scatter",
            line=dict(shape="spline", smoothing=smoothing),
        )
        layout = go.Layout(title=plotTitle, xaxis=dict(title=x), yaxis=dict(title=y))
        fig = go.Figure(data=[trace], layout=layout)
        fig = self.setPlotProperties(
            fig=fig,
            hoverTemplate="  %{x},  %{y}  ",
            figSize=figSize,
            showXAxis=True,
            showYAxis=False,
        )
        ofl.plot(fig)

    def barPlot(self):
        barOneTrace = go.Bar(
            x=["giraffes", "orangutans", "monkeys"], y=[20, 14, 23], name="SF Zoo"
        )

        # Create trace 2 for Los Angeles Zoo
        barTwoTrace = go.Bar(
            x=["giraffes", "orangutans", "monkeys"], y=[12, 18, 29], name="LA Zoo"
        )

        # Create figure object and visualize plot
        fig = go.Figure(
            data=[barOneTrace, barTwoTrace], layout=go.Layout(barmode="stack")
        )
        fig = self.setPlotProperties(
            fig=fig,
            showXAxis=True,
            showYAxis=True,
            hoverTemplate=" %{x} ",
            figSize=(480, 480),
        )
        ofl.plot(fig)

    def piePlot(self):
        # Creating labels
        labels = ["Oxygen", "Hydrogen", "Carbon_Dioxide", "Nitrogen"]

        # Creating values
        values = [4500, 2500, 1053, 500]

        # Creating the Pie plot object using the labels and values
        pieTrace = go.Pie(
            labels=labels,
            values=values,
            hoverinfo="label+percent",
            textinfo="percent+label",
            textfont=dict(size=20),
            marker=dict(
                colors=["#FEBFB3", "#E1396C", "#96D38C", "#D0F9B1"],
                line=dict(color="#000000", width=2),
            ),
        )

        fig = go.Figure()
        fig.add_trace(pieTrace)

        fig = self.setPlotProperties(fig=fig)

        # Visualizing the plot
        ofl.plot(fig)

    def donutPlot(self):
        fig = go.Figure(
            {
                # key is data and value is a list of objects - one for each data trace
                "data": [
                    {
                        # defining values
                        "values": [16, 15, 12, 6, 5, 4, 42],
                        # defining labels
                        "labels": [
                            "US",
                            "China",
                            "European Union",
                            "Russian Federation",
                            "Brazil",
                            "India",
                            "Rest of World",
                        ],
                        # defining domain - the position of this subplot starts from 0 and occupies first 48% of x axis
                        "domain": {"x": [0, 0.48]},
                        # Name of the data object
                        "name": "GHG Emissions",
                        # Information to be displayed on hover
                        "hoverinfo": "label+percent+name",
                        # hole which creates the donut
                        "hole": 0.4,
                        # type of chart is defined here
                        "type": "pie",
                    },
                    {
                        "values": [27, 11, 25, 8, 1, 3, 25],
                        "labels": [
                            "US",
                            "China",
                            "European Union",
                            "Russian Federation",
                            "Brazil",
                            "India",
                            "Rest of World",
                        ],
                        "text": ["CO2"],
                        "textposition": "inside",
                        # defining domain - the position of this subplot starts from 0.52 and occupies remaining 48% of x axis, 4% is padding
                        "domain": {"x": [0.52, 1]},
                        "name": "CO2 Emissions",
                        "hoverinfo": "label+percent+name",
                        "hole": 0.4,
                        "type": "pie",
                    },
                ],
                "layout": {
                    "title": "Global Emissions 1990-2011",
                    "annotations": [
                        {
                            "font": {"size": 20},
                            "showarrow": False,
                            "text": "GHG",
                            "x": 0.20,
                            "y": 0.5,
                        },
                        {
                            "font": {"size": 20},
                            "showarrow": False,
                            "text": "CO2",
                            "x": 0.8,
                            "y": 0.5,
                        },
                    ],
                },
            }
        )

        fig = self.setPlotProperties(
            fig=fig,
        )
        ofl.plot(fig)

    def bubblePlot(self):
        # Create scatter plot object, but add color and size parameters to the 'marker' dictionary
        scatterTrace = go.Scatter(
            x=[1, 1.5, 1.48, 1.75, 1.85, 1.95, 2, 2.25, 2.25, 2.28, 2.5, 2.5, 3],
            y=[12, 12, 12.3, 13, 12.1, 12.2, 12, 11.5, 12.5, 12.25, 11.2, 11.5, 13.5],
            mode="markers",
            marker=dict(
                color=self.getDiscreteNColors(13),
                size=[20, 50, 35, 40, 45, 40, 45, 50, 55, 60, 40, 60, 10],
            ),
        )

        fig = go.Figure()
        fig.add_trace(scatterTrace)

        fig = self.setPlotProperties(
            fig=fig,
            showXAxis=True,
            showYAxis=True,
            xAxisTitle="X",
            yAxisTitle="Y",
            figSize=(480, 480),
            plotMargin=10,
        )

        ofl.plot(fig)

    # ----------------------------------------------------- Color Picker Utils ---------------------------------------------------- #

    def getDiscreteNColors(self, n: int, colorScale=None) -> list:
        if colorScale is None:
            colorScale = self.defaultColorScale

        colorStart = colorScale[0]
        colorMid1 = colorScale[int(len(colorScale) / 2)]
        colorMid2 = colorScale[int(len(colorScale) / 2) + 1]
        colorEnd = colorScale[-1]
        nColors1 = pc.n_colors(colorStart, colorMid1, int(n / 2), colortype="rgb")
        nColors2 = pc.n_colors(
            colorMid2, colorEnd, (n - len(nColors1)), colortype="rgb"
        )
        nColors = nColors1 + nColors2

        return nColors

    def getColorFromScale(self, colorScaleName, intermed):
        from _plotly_utils.basevalidators import ColorscaleValidator

        cv = ColorscaleValidator("colorscale", "")
        colorScale = cv.validate_coerce(colorScaleName)
        if hasattr(intermed, "__iter__"):
            return [self.getContinuousColor(colorScale, x) for x in intermed]
        return self.getContinuousColor(colorScale, intermed)

    def getContinuousColor(self, colorScale, intermed):
        """
        Plotly continuous colorscales assign colors to the range [0, 1]. This function computes the intermediate
        color for any value in that range.

        Plotly doesn't make the colorscales directly accessible in a common format.
        Some are ready to use:

            colorscale = plotly.colors.PLOTLY_SCALES["Greens"]

        Others are just swatches that need to be constructed into a colorscale:

            viridis_colors, scale = plotly.colors.convert_colors_to_same_type(plotly.colors.sequential.Viridis)
            colorscale = plotly.colors.make_colorscale(viridis_colors, scale=scale)

        :param colorscale: A plotly continuous colorscale defined with RGB string colors.
        :param intermed: value in the range [0, 1]
        :return: color in rgb string format
        :rtype: str
        """
        if len(colorScale) < 1:
            raise ValueError("colorScale must have at least one color")

        hex_to_rgb = lambda c: "rgb" + str(ImageColor.getcolor(c, "RGB"))

        if intermed <= 0 or len(colorScale) == 1:
            c = colorScale[0][1]
            return c if c[0] != "#" else hex_to_rgb(c)
        if intermed >= 1:
            c = colorScale[-1][1]
            return c if c[0] != "#" else hex_to_rgb(c)

        for cutoff, color in colorScale:
            if intermed > cutoff:
                low_cutoff, low_color = cutoff, color
            else:
                high_cutoff, high_color = cutoff, color
                break

        if (low_color[0] == "#") or (high_color[0] == "#"):
            # some color scale names (such as cividis) returns:
            # [[loc1, "hex1"], [loc2, "hex2"], ...]
            low_color = hex_to_rgb(low_color)
            high_color = hex_to_rgb(high_color)

        return pc.find_intermediate_color(
            lowcolor=low_color,
            highcolor=high_color,
            intermed=((intermed - low_cutoff) / (high_cutoff - low_cutoff)),
            colortype="rgb",
        )
