import dash
from dash import html, Input, Output, ALL, callback, ctx, _dash_renderer, dcc, State
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_leaflet as dl
from dash_extensions.javascript import assign
import json
import dash_leaflet.express as dlx
import pandas as pd


def get_info(feature=None, selected_pois=None, transport_mode="walk"):
    # Default header when no feature is hovered
    header = [html.H4("Hover over a block for details")]
    if not feature:
        return header + [html.P("")]
    
    if transport_mode == "walk":
        transport_msg = html.B("Walking time to:")
    elif transport_mode == "bike":
        transport_msg = html.B("Biking time to:")
    elif transport_mode == "pt":
        transport_msg = html.B("Public transit time to:")
    elif transport_mode == "car":
        transport_msg = html.B("Driving time to:")
    
    # Load the CSV file into a pandas DataFrame
    time_data = pd.read_csv('assets/prueba.csv', dtype={"Erreferentz": str})
    
    # Extract properties from the feature
    municipio = feature["properties"].get("Municipio", "Unknown")
    density_str = feature["properties"].get("density", "N/A")
    cusec = feature["properties"].get("CUSEC", "N/A")
    ref = feature["properties"].get("Erreferentz", None)
    
    # Ensure `ref` is a string for comparison
    if time_data is not None and ref:
        ref = str(ref).strip()  # Convert and clean `ref`
        # Filter the DataFrame for the matching `Erreferentz`
        row = time_data[time_data["Erreferentz"] == ref]
        if not row.empty:
            bike_time = row["color_1_bike"].iloc[0] if "color_1_bike" in row else "N/A"
            walk_time = row["color_1_walk"].iloc[0] if "color_1_walk" in row else "N/A"
    
    # Build the HTML output
    return [
        #html.B("Municipio: "), f"{municipio}", html.Br(),
        #html.B("Density: "), f"{density_str} people / mi²", html.Br(),
       # html.B("CUSEC: "), f"{cusec}", html.Br(),
       # html.B("Walk Time: "), f"{walk_time} minutes", html.Br(),
       # html.B("Bike Time: "), f"{bike_time} minutes", html.Br(),
        transport_msg, html.Br(),
        html.B("Selected POIs: "), f"{', '.join(selected_pois)}", html.Br(),
    ]

# Create info control.
info = html.Div(children=get_info(), id="info", className="info",
                style={"position": "absolute", "top": "10px", "right": "10px", "zIndex": "1000"})

# styling of the polygons (default & when hovered)
visual_style = assign(""" 
    function(feature) {
        const selectedColor = feature.properties.selectedColor || '#6baed6'; // Default color (blue)
        return {
            color: '#3182bd',
            weight: 2,
            opacity: 0.8,
            fillColor: selectedColor,
            fillOpacity: 0.4
        };
    }
""")

# hover interaction
on_each_feature = assign("""
    function(feature, layer) {
        // Mouseover event
        layer.on('mouseover', function() {
            const CUSEC = feature.properties['CUSEC'];

            // Highlight all polygons with the same CUSEC
            this._map.eachLayer((otherLayer) => {
                if (otherLayer.feature && otherLayer.feature.properties['CUSEC'] === CUSEC) {
                    if (!otherLayer.options._originalStyle) {
                        // Save the original style if not already saved
                        otherLayer.options._originalStyle = {
                            color: otherLayer.options.color,
                            weight: otherLayer.options.weight,
                            opacity: otherLayer.options.opacity,
                            fillColor: otherLayer.options.fillColor,
                            fillOpacity: otherLayer.options.fillOpacity,
                        };
                    }
                    otherLayer.setStyle({
                        color: '#2b5775',
                        weight: 3,
                        opacity: 1,
                        fillOpacity: 0.7
                    });
                }
            });
        });

        // Mouseout event
        layer.on('mouseout', function() {
            const CUSEC = feature.properties['CUSEC'];

            // Reset the style of all polygons with the same CUSEC
            this._map.eachLayer((otherLayer) => {
                if (otherLayer.feature && otherLayer.feature.properties['CUSEC'] === CUSEC) {
                    const originalStyle = otherLayer.options._originalStyle;
                    if (originalStyle) {
                        otherLayer.setStyle(originalStyle);
                    }
                }
            });
        });

        // Tooltip
        layer.bindTooltip(
            `<strong>${feature.properties['CUSEC']}</strong><br>Municipio: ${feature.properties['Municipio']}`,
            { permanent: false, direction: 'top' }
        );
    }
""")

# Dash app (initialize like here always, if not the dmc components don't work, we need to make sure the React version is 18.2.0)
# React 18 Issue: Dash Mantine Components is based on REACT 18. You must set the env variable REACT_VERSION=18.2.0 before starting up the app.
# https://www.dash-mantine-components.com/getting-started#:~:text=React%2018%20Issue,up%20the%20app.
_dash_renderer._set_react_version("18.2.0")
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dmc.styles.ALL])
server = app.server

# Load geojson polygons
with open("assets/prueba.geojson", "r") as f:
    geojson = json.load(f)

# Set the initial selected color to blue (default)
for feature in geojson['features']:
    feature['properties']['selectedColor'] = '#6baed6'  # Default color (blue)

# Load POI GeoJSON files
with open("assets/filtered-centros-educativos.geojson", "r") as f:
    schools_geojson = json.load(f)

with open("assets/filtered-bibliotecas.geojson", "r") as f:
    libraries_geojson = json.load(f)

with open("assets/hospitales.geojson", "r") as f:
    hospitals_geojson = json.load(f)

# Dictionaries by POI categories
eat_layers = [
    {"label": "Special Food Services", "value": "color_1", "geojson": schools_geojson, "checked": False},
    {"label": "Restaurants", "value": "color_2", "geojson": libraries_geojson, "checked": False},
    {"label": "Cafes & bakeries", "value": "color_3","geojson": hospitals_geojson, "checked": False},
    {"label": "Bars", "value": "color_4","geojson": hospitals_geojson, "checked": False},
]

healthcare_layers = [
    {"label": "Clinics & local healthcare centers", "value":"color_5", "geojson":hospitals_geojson,"checked": False},
    {"label": "Hospitals", "value":"color_6","geojson":libraries_geojson,"checked": False},
    {"label": "Nursing & Residential Care", "checked": False},
    {"label": "Dentists", "checked": False},
    {"label": "Psychologist", "checked": False},
]

leisure_layers = [
    {"label": "Hairdresser & Barbery", "checked": False},
    {"label": "Personal Wellness", "checked": False},
]

professional_layers = [
    {"label": "Administrative and Support Services", "checked": False},
    {"label": "Finance", "checked": False},
    {"label": "Insurance Agency", "checked": False},
    {"label": "Management of Companies", "checked": False},
    {"label": "Professional Services", "checked": False},
    {"label": "Real Estate", "checked": False},
    {"label": "Travel Agency", "checked": False},
]

pharmacy_layers = [
    {"label": "Pharmacy", "checked": False},
]

service_layers = [
    {"label": "Car Rental", "checked": False},
    {"label": "Car Repair", "checked": False},
    {"label": "Death Care Services", "checked": False},
    {"label": "Fuel Station", "checked": False},
    {"label": "Laundry", "checked": False},
    {"label": "Locksmith Errands", "checked": False},
    {"label": "Moving Company", "checked": False},
    {"label": "Parking", "checked": False},
    {"label": "Post Office", "checked": False},
    {"label": "Storage", "checked": False},
    {"label": "Veterinary Services", "checked": False},
    {"label": "Waste Management", "checked": False},
]

hotel_layers = [
    {"label": "Hotel and Lodging", "checked": False},
]

consumergoods_layers = [
    {"label": "Book Store", "checked": False},
    {"label": "Clothing Store", "checked": False},
    {"label": "Cosmetics Retail", "checked": False},
    {"label": "Department Store", "checked": False},
    {"label": "Florist", "checked": False},
    {"label": "Gift and Souvenir", "checked": False},
    {"label": "Hobby Retailers", "checked": False},
    {"label": "Jewelry Stores", "checked": False},
    {"label": "Optical Goods", "checked": False},
    {"label": "Pet Store", "checked": False},
    {"label": "Shoe Store", "checked": False},
    {"label": "Used Merchandise", "checked": False},
    {"label": "Warehouse", "checked": False},
]

durablegoods_layers = [
    {"label": "Car Dealer", "checked": False},
    {"label": "Home Goods Store", "checked": False},
    {"label": "Wholesale Trade", "checked": False},
]

grocery_layers = [
    {"label": "Convenience Corner Store", "checked": False},
    {"label": "Grocery or Supermarket", "checked": False},
    {"label": "Liquor Store", "checked": False},
    {"label": "Specialty Food Retailers", "checked": False},
]

cultural_layers = [
    {"label": "Art Gallery", "checked": False},
    {"label": "Library", "checked": False},
    {"label": "Museum", "checked": False},
]

entertainment_layers = [
    {"label": "Amusement Park", "checked": False},
    {"label": "Bowling", "checked": False},
    {"label": "Casino", "checked": False},
    {"label": "Movie Theater", "checked": False},
    {"label": "Performing Arts", "checked": False},
    {"label": "Spectator Sports", "checked": False},
    {"label": "Zoos and Nature Parks", "checked": False},
]

leisurewellness_layers = [
    {"label": "Golf Courses", "checked": False},
    {"label": "Gym", "checked": False},
    {"label": "Marinas", "checked": False},
]

train_layers = [
    {"label": "Euskotren", "checked": False},
    {"label": "Renfe Cercanías", "checked": False},
]

bus_layers=[
    {"label": "Lurraldebus", "checked": False},
    {"label": "DBus", "checked": False},
]

bike_layers=[
    {"label": "DBizi", "checked": False},
]

religious_layers = [
    {"label": "Religious Centers", "checked": False},
]

poi_menu = html.Div(
    dbc.Accordion(
        [
            # Eat Section
            dbc.AccordionItem(
                dmc.MantineProvider(
                    children=[
                        html.H6("Food & Beverage", style={"marginTop": "10px", "marginBottom": "5px"}),
                        html.Div([
                            dmc.Checkbox(
                                id={"type": "eat-item", "index": i},
                                label=item["label"],
                                checked=item["checked"],
                                style={"marginTop": "5px", "marginLeft": "10px"}
                            )
                            for i, item in enumerate(eat_layers)
                        ])
                    ]
                ),
                title="Eat",
                item_id="eatery",
                style={  # Apply style here
                    "maxHeight": "150px",  # Adjust as needed
                    "overflowY": "auto",  # Scrollbar only when necessary
                },
            ),
            # Errands Section
            dbc.AccordionItem(
                dmc.MantineProvider(
                    children=[
                        # Healthcare
                        html.Div([
                            html.H6("Healthcare", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "healthcare-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(healthcare_layers)
                            ])
                        ]),
                        # Leisure
                        html.Div([
                            html.H6("Leisure & Wellness", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "leisure-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(leisure_layers)
                            ])
                        ]),
                        # Professional Services
                        html.Div([
                            html.H6("Professional Services", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "professional-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(professional_layers)
                            ])
                        ]),
                        # Retail (Pharmacy)
                        html.Div([
                            html.H6("Retail (Pharmacy)", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "pharmacy-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(pharmacy_layers)
                            ])
                        ]),
                        # Service
                        html.Div([
                            html.H6("Service", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "service-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(service_layers)
                            ])
                        ]),
                    ]
                ),
                title="Errands",
                item_id="errands",
                style={  # Apply style here
                    "maxHeight": "150px",  # Adjust as needed
                    "overflowY": "auto",  # Scrollbar only when necessary
                },
            ),
            # Lodging Section
            dbc.AccordionItem(
                dmc.MantineProvider(
                    children=[
                        # Hotel
                        html.Div([
                            html.H6("Hotel", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "hotel-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(hotel_layers)
                            ])
                        ]),
                    ]
                ),
                title="Lodging",
                item_id="lodging",
                style={  # Apply style here
                    "maxHeight": "150px",  # Adjust as needed
                    "overflowY": "auto",  # Scrollbar only when necessary
                },
            ),
            # Shop Section
            dbc.AccordionItem(
                dmc.MantineProvider(
                    children=[
                        # Retail (Consumer Goods)
                        html.Div([
                            html.H6("Consumer Goods", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "consumergoods-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(consumergoods_layers)
                            ])
                        ]),
                        # Retail (Durable Goods)
                        html.Div([
                            html.H6("Durable Goods", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "durablegoods-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(durablegoods_layers)
                            ])
                        ]),
                        # Retail (Grocery)
                        html.Div([
                            html.H6("Grocery", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "grocery-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(grocery_layers)
                            ])
                        ]),
                    ]
                ),
                title="Shop",
                item_id="shop",
                style={  # Apply style here
                    "maxHeight": "150px",  # Adjust as needed
                    "overflowY": "auto",  # Scrollbar only when necessary
                },
            ),
            # Recreation Section
            dbc.AccordionItem(
                dmc.MantineProvider(
                    children=[
                        # Cultural
                        html.Div([
                            html.H6("Cultural", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "cultural-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(cultural_layers)
                            ])
                        ]),
                        # Entertainment
                        html.Div([
                            html.H6("Entertainment", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "entertainment-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(entertainment_layers)
                            ])
                        ]),
                        # Leisure & Wellness
                        html.Div([
                            html.H6("Leisure & Wellness", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "leisurewellness-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(leisurewellness_layers)
                            ])
                        ]),
                    ]
                ),
                title="Recreation",
                item_id="recreation",
                style={  # Apply style here
                    "maxHeight": "150px",  # Adjust as needed
                    "overflowY": "auto",  # Scrollbar only when necessary
                },
            ),
            # Transport Section
            dbc.AccordionItem(
                dmc.MantineProvider(
                    children=[
                        # Train
                        html.Div([
                            html.H6("Train", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "train-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(train_layers)
                            ])
                        ]),
                        # Bus
                        html.Div([
                            html.H6("Bus", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "bus-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(bus_layers)
                            ])
                        ]),
                        # Bike
                        html.Div([
                            html.H6("Bike", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "bike-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "5px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(bike_layers)
                            ])
                        ]),
                    ]
                ),
                title="Transport",
                item_id="transport",
                style={  # Apply style here
                    "maxHeight": "150px",  # Adjust as needed
                    "overflowY": "auto",  # Scrollbar only when necessary
                },
            ),
            # Errands Section
            dbc.AccordionItem(
                dmc.MantineProvider(
                    children=[
                        # Religious
                        html.Div([
                            html.H6("Religious", style={"marginTop": "10px", "marginBottom": "5px"}),
                            html.Div([
                                dmc.Checkbox(
                                    id={"type": "religious-item", "index": i},
                                    label=item["label"],
                                    checked=item["checked"],
                                    style={"marginTop": "0px", "marginLeft": "33px"}
                                )
                                for i, item in enumerate(religious_layers)
                            ])
                        ]),
                    ]
                ),
                title="Others",
                item_id="others",
                style={  # Apply style here
                    "maxHeight": "150px",  # Adjust as needed
                    "overflowY": "auto",  # Scrollbar only when necessary
                },
            ),
        ],
        id="accordion",
        active_item="eat",
    ),
    style={
        "backgroundColor": "rgba(255, 255, 255, 0.9)",
        "padding": "2px",
        "borderRadius": "5px",
        "width": "360px",
    },
)

data_mt = [["walk", "Walk"], ["bike", "Bike"], ["pt", "Public Transit"], ["car", "Car"]]

# Define the first radio group as a separate component
mt_menu = dmc.MantineProvider(
    children=[
        dmc.RadioGroup(
            children=dmc.Group(
                [dmc.Radio(label, value=value) for value, label in data_mt],
               my=10,
            ),
            id="transport-choice",
            value="walk",
            label="Select a mode of transport",
            size="sm",
        )
    ]
)

data_demog = [["choiceA", "Population Density"], ["choiceB", "Foreign Population"], ["choiceC", "Income Level"]]

# Define the second radio group as a separate component
demog_menu = dmc.MantineProvider(
    children=[
        dmc.RadioGroup(
            children=dmc.Stack(
                [dmc.Radio(label, value=value) for value, label in data_demog],
                my=10,
            ),
            id="radiogroup-2",
            value="choiceA",
            label="Select the demographic data to display",
            size="sm",
            mb=10,
        )
    ]
)

buttons = dmc.MantineProvider(
    children=[
        dmc.Group([
        dmc.Button("Apply", variant="filled", size="md", id="apply-button"),
    ],
        id="button-group",
        gap=40,
        justify="center",
    )
    ]
)

# Define map and data
classes = [0, 3, 6, 10, 15, 20, 25]
colorscale = ['#00572a', '#7CB342', '#FFFF00', '#FFA500', '#D50000', '#8f0340', '#6a1717']

# Define categories for color bar
ctg = [f"{cls}-{classes[i + 1]}" for i, cls in enumerate(classes[:-1])] + [f"{classes[-1]}+"]
colorbar = dlx.categorical_colorbar(categories=ctg, colorscale=colorscale, width=300, height=30, position="bottomright")


# Layout
app.layout = html.Div(
    [
        # Map Component
        dl.Map(
            [
                dl.TileLayer(url='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', maxZoom=20),
                dl.GeoJSON(
                    id="geojson-layer",
                    data=geojson,  # Replace with your actual endpoint
                    options=dict(style=visual_style, onEachFeature=on_each_feature),
                ),
                dl.LayerGroup(id="map-points"),
                colorbar,
                dl.ZoomControl(position="bottomright", id="zoom"),
            ],
            center=[43.16, -2.2],
            zoom=11,
            style={"height": "100vh", "width": "100%"},
            zoomControl=False,  # Disable default zoom control
        ),
        # Sidebar Container
        html.Div(
            [
                # All Menus in One Container
                html.Div(
                    [
                        html.Div(
                            mt_menu,
                            style={
                                "marginBottom": "2px",
                                "padding": "10px",
                                "backgroundColor": "white",
                                "borderRadius": "5px",
                            },
                        ),
                        html.Div(
                            poi_menu,
                        ),
                        html.Div(
                            demog_menu,
                            style={
                                "marginBottom": "2px",
                                "padding": "10px",
                                "backgroundColor": "white",
                                "borderRadius": "5px",
                                
                            },
                        ),
                        html.Div(
                            buttons,
                            style={
                                
                                "borderRadius": "5px",
                                "backgroundColor": "rgba(255, 255, 255)",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "2px",  # Space between menus
                    },
                ),
            ],
            style={
                "position": "absolute",
                "top": "10px",
                "left": "10px",
                "width": "380px",
                "backgroundColor": "rgba(255, 255, 255)",
                "zIndex": 1000,
                "padding": "10px",
                "borderRadius": "5px",
                "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.2)",
            },
        ),
        info,
        dcc.Store(id="selected-pois", data=[]),  # Store for POIs (empty list as default)
    ]
)

# Update the callback to display the hovered feature's information, including CUSEC
@callback(
    Output("info", "children"),  # Update the info display
    [Input("geojson-layer", "hoverData"),  # Trigger when hovering over GeoJSON layer
     Input("selected-pois", "data"),  # Access selected POIs from the dcc.Store
     State("transport-choice", "value")]  # Access selected transport mode from the dcc.Store
)
def info_hover(feature, selected_pois, transport_mode):
    # Use the feature and selected_pois data in your function
    return get_info(feature, selected_pois, transport_mode)


@app.callback(
    [Output("geojson-layer", "data"),  # Update GeoJSON layer
     Output("map-points", "children"),  # Update map points
     Output("selected-pois", "data")],  # Update selected POIs in the Store
    [Input("apply-button", "n_clicks")],  # Trigger on Apply button click
    [State({"type": ALL, "index": ALL}, "checked"),  # Read checkbox states
     State("transport-choice", "value")]  # Read mode of transport selection
)
def update_color_and_map(n_clicks, checked_values, transport_mode):
    if not n_clicks:  # Prevent callback from running before Apply is clicked
        return dash.no_update, dash.no_update, dash.no_update

    # Define color priority in order from worst to best
    color_priority = ['#6a1717', '#8f0340', '#D50000', '#FFA500', '#FFFF00', '#7CB342', '#00572a']
    
    # Combine all layers into one list (in the same order as the checkboxes)
    all_layers = [
        eat_layers, healthcare_layers, leisure_layers, professional_layers,
        pharmacy_layers, service_layers, hotel_layers, consumergoods_layers,
        durablegoods_layers, grocery_layers, cultural_layers, entertainment_layers,
        leisurewellness_layers, train_layers, bus_layers, bike_layers, religious_layers
    ]
    
    selected_pois = []  # To store the selected colors
    map_points = []  # To store the map points
    layer_idx = 0  # To track the index across all layers
    
    # Iterate over each layer group (each list of layers)
    for layer_group in all_layers:
        for idx, checked in enumerate(checked_values[layer_idx:layer_idx + len(layer_group)]):
            if checked:
                layer = layer_group[idx]
                selected_pois.append(layer["value"])  # Get the column name (e.g., "hospital")
                
                # Process map points for this checked layer
                for feature in layer["geojson"]["features"]:
                    # Validate coordinates
                    coordinates = feature.get("geometry", {}).get("coordinates")
                    if coordinates and len(coordinates) >= 2:
                        lon, lat = coordinates
                        if lat is not None and lon is not None:
                            map_points.append(
                                dl.Marker(
                                    position=[lat, lon],  # Use [lat, lon]
                                    children=[dl.Popup(layer["label"])]
                                )
                            )
        layer_idx += len(layer_group)  # Move the index forward by the number of layers in the group

    # Now prioritize the colors for each feature
    for feature in geojson['features']:
        feature_colors = []

        # Iterate over the selected column names (e.g., "hospital") and gather colors
        for column in selected_pois:
            # Append the mode of transport (e.g., "hospital_bike" if the mode is "bike")
            column_with_mode = f"{column}_{transport_mode}"
            
            # Print the column name to debug
            print(f"Accessing column: {column_with_mode}")
            
            # Get the color stored in the feature's specific column (e.g., "hospital_bike")
            color = feature['properties'].get(column_with_mode)
            if color in color_priority:
                feature_colors.append(color)

        # Prioritize the colors: choose the highest priority color (first match in color_priority)
        if feature_colors:
            # Choose the best color based on priority
            for color in color_priority:
                if color in feature_colors:
                    feature['properties']['selectedColor'] = color
                    break
        else:
            feature['properties']['selectedColor'] = '#6baed6'  # Default color if no selection

    # Ensure geojson is updated with the selected color
    return geojson, map_points, selected_pois

if __name__ == "__main__":
    app.run_server(debug=False)
