import logging

import branca
import folium
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class Mapper:
    def __init__(self, input_csv):
        self.style = 'cartodbpositron'
        self.map = folium.Map(location=(0, 0), zoom_start=6, tiles=self.style)
        self.df = pd.read_csv(input_csv)

    def create_basemap(self, centre_lat, centre_lon, zoom_level):
        self.map = folium.Map(location=(centre_lat, centre_lon), zoom_start=zoom_level, tiles=self.style)
        return self.map

    @staticmethod
    def get_frame(url, width, height):
        html = """ 
            <!doctype html>
        <html>
        <iframe id="myIFrame" width="{}" height="{}" src={}""".format(width, height, url) + """ frameborder="0"></iframe>
        <script type="text/javascript">
        var resizeIFrame = function(event) {
            var loc = document.location;
            if (event.origin != loc.protocol + '//' + loc.host) return;

            var myIFrame = document.getElementById('myIFrame');
            if (myIFrame) {
                myIFrame.style.height = event.data.h + "px";
                myIFrame.style.width  = event.data.w + "px";
            }
        };
        if (window.addEventListener) {
            window.addEventListener("message", resizeIFrame, false);
        } else if (window.attachEvent) {
            window.attachEvent("onmessage", resizeIFrame);
        }
        </script>
        </html>"""
        return html

    def create_map_with_points(self, reference_df, zoom_level=13):
        ref_df = pd.read_csv(reference_df)
        interested = ref_df[ref_df['category'] == 'interested']
        remove = ref_df[ref_df['category'] == 'remove']
        interested_list = [] if len(interested) == 0 else interested['property_id'].tolist()
        remove_list = [] if len(remove) == 0 else remove['property_id'].tolist()
        # remove_df = pd.read_csv(remove_df)
        # interest_df = pd.read_csv(interested_df)
        # TODO reinstate above dfs

        centre_lat = self.df['latitude'].mean()
        centre_lon = self.df['longitude'].mean()
        self.create_basemap(centre_lat, centre_lon, zoom_level)
        for index, row in self.df.iterrows():
            if not np.isnan(row['latitude']) and row['id'] not in remove_list:
                ring_colour = 'black'
                fill_colour = 'green' if row['id'] in interested_list else 'blue'
                score = row['total_score']
                tooltip = f"""id: {row["id"]},  score: {score},  beds: {row["beds"]},  tenure: {row["tenure"]},
                price: {row["price"]},  travel: {row["travel_time_loc1"]} (mins), 
                 travel 2: {row["travel_time_loc2"]} (mins), 
                   {row['url']},  <a href = "{row['url']}">open listing</a>"""
                iframe = branca.element.IFrame(html=tooltip, width=1200, height=750)
                popup = folium.Popup(iframe, parse_html=True, max_width=2650)
                folium.CircleMarker(location=(row['latitude'], row['longitude']), radius=score, color=ring_colour,
                                    fill_color=fill_colour, fill=True,
                                    popup=popup).add_to(self.map)
            else:
                logger.debug(f'skipping index: {index} (NaN coords)')
        return self.map

    def save_map(self, output_filepath):
        logger.info('saving file in %s' % output_filepath)
        self.map.save(output_filepath)
