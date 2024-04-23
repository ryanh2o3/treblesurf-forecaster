import flask
from flask import Flask, render_template, send_from_directory, jsonify, request
import os
from api.forecastFetcher import *

# Create the application.
APP = flask.Flask(__name__, static_folder='static')

@APP.route('/')
def index():
    """ Displays the index page accessible at '/'
    """
    return flask.render_template('index.html')

#uses the getCOordinates function to get the latitude and longitude of a location
@APP.route("/forecast")
def get_Forecast():
    retrieveForecast()
    return 'Forecast retrieved', 200

if __name__ == '__main__':
    APP.debug=True
    APP.run()
