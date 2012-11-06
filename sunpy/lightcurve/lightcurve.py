"""
LightCurve is a generic LightCurve class from which all other LightCurve classes 
inherit from.
"""
from __future__ import absolute_import

#pylint: disable=E1101,E1121,W0404,W0612,W0613
__authors__ = ["Keith Hughitt"]
__email__ = "keith.hughitt@nasa.gov"

import os
import pandas
import sunpy
import shutil
import urllib2
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime
from types import NoneType

from sunpy.time import is_time, TimeRange
from sunpy.util.cond_dispatch import ConditionalDispatch, run_cls

class LightCurve(object):
    """
    LightCurve(filepath)

    A generic light curve object.

    Parameters
    ----------
    args : filepath, url, or start and end dates
        The input for a LightCurve object should either be a filepath, a URL,
        or a date range to be queried for the particular instrument.

    Attributes
    ----------
    data : pandas.DataFrame
        An pandas DataFrame prepresenting one or more fields as they vary with 
        respect to time.
    header : string, dict
        The comment string or header associated with the light curve input

    Examples
    --------
    >>> import sunpy
    >>> import datetime
    >>> base = datetime.datetime.today()
    >>> dates = [base - datetime.timedelta(minutes=x) for x in 
    range(0, 24 * 60)]
    >>> light_curve = sunpy.lightcurve.LightCurve({"param1": range(24 * 60)}, 
    index=dates)
    >>> light_curve.show()

    References
    ----------
    | http://pandas.pydata.org/pandas-docs/dev/dsintro.html

    """
    _cond_dispatch = ConditionalDispatch()
    create = classmethod(_cond_dispatch.wrapper())
    
    def __init__(self, data, header=None):     
        self.data = data
        self.header = header
    
    @classmethod
    def from_time(cls, time, **kwargs):
        date = sunpy.time.parse_time(time)
        url = cls._get_url_for_date(date)
        filepath = cls._download(
            url, kwargs, err="Unable to download data for  specified date"
        )
        return cls.from_file(filepath)
    
    @classmethod
    def from_range(cls, from_, to, **kwargs):
        url = cls._get_url_for_date_range(from_, to)
        filepath = self._download(
            url, kwargs, 
            err = "Unable to download data for specified date range"
        )
        return cls.from_file(filepath)
    
    @classmethod
    def from_timerange(cls, timerange, **kwargs):
        url = cls._get_url_for_date_range(timerange)
        err = "Unable to download data for specified date range"
        filepath = self._download(url, err, kwargs)   
        return cls.from_file(filepath)       
    
    @classmethod
    def from_file(cls, filename):
        filename = os.path.expanduser(filename)
        
        header, data = cls._parse_filepath(filename)
        return cls(data, header)
    
    @classmethod
    def from_url(cls, url, **kwargs):
        try:
            filepath = cls._download(url, kwargs)
        except (urllib2.HTTPError, urllib2.URLError, ValueError):
            err = ("Unable to read location. Did you "
                   "specify a valid filepath or URL?")
            raise ValueError(err)
        return cls.from_file(filepath)
    
    @classmethod
    def from_data(cls, data, index=None, header=None):
        return cls(
            pandas.DataFrame(data, index=index),
            header
        )
    
    @classmethod
    def from_yesterday(cls):
        return cls.from_url(cls._get_default_uri())
    
    @classmethod
    def from_dataframe(cls, dataframe, header=None):
        return cls(dataframe, header)
    
    def plot(self, **kwargs):
        """Plot a plot of the light curve"""
        axes = self.data.plot(**kwargs)
        return axes.get_figure()
    
    def show(self, **kwargs):
        """Shows a plot of the light curve"""
        fig = self.plot(**kwargs)
        fig.show()
        
        return fig
    
    @staticmethod
    def _download(uri, kwargs, 
                  err='Unable to download data at specified URL'):
        """Attempts to download data at the specified URI"""
        _filename = os.path.basename(uri).split("?")[0]
        
        # user specifies a download directory
        if "directory" in kwargs:
            download_dir = os.path.expanduser(kwargs["directory"])
        else:
            download_dir = sunpy.config.get("downloads", "download_dir")
        
        # overwrite the existing file if the keyword is present
        if "overwrite" in kwargs:
            overwrite = kwargs["overwrite"]
        else:
            overwrite = False
        
        # If the file is not already there, download it
        filepath = os.path.join(download_dir, _filename)

        if not(os.path.isfile(filepath)) or (overwrite and 
                                             os.path.isfile(filepath)):
            try:
                response = urllib2.urlopen(uri)
            except (urllib2.HTTPError, urllib2.URLError):
                raise urllib2.URLError(err)
            with open(filepath, 'wb') as fp:
                shutil.copyfileobj(response, fp)
                    
        return filepath
    
    @classmethod
    def _get_default_uri(cls):
        """Default data to load when none is specified"""
        msg = "No default action set for %s"
        raise NotImplementedError(msg % cls.__name__)
    
    @classmethod
    def _get_url_for_date(cls, date):
        """Returns a URL to the data for the specified date"""
        msg = "Date-based downloads not supported for for %s"
        raise NotImplementedError(msg % cls.__name__)
    
    @classmethod
    def _get_url_for_date_range(cls, *args, **kwargs):
        """Returns a URL to the data for the specified date range"""
        msg = "Date-range based downloads not supported for for %s"
        raise NotImplementedError(msg % cls.__name__)
    
    @staticmethod
    def _parse_csv(filepath):
        """Place holder method to parse CSV files."""
        msg = "Generic CSV parsing not yet implemented for LightCurve"
        raise NotImplementedError(msg)
    
    @staticmethod
    def _parse_fits(filepath):
        """Place holder method to parse FITS files."""
        msg = "Generic FITS parsing not yet implemented for LightCurve"
        raise NotImplementedError(msg)
    
    @classmethod
    def _parse_filepath(cls, filepath):
        filename, extension = os.path.splitext(filepath)
        
        if extension.lower() in (".csv", ".txt"):
            return cls._parse_csv(filepath)
        else:
            return cls._parse_fits(filepath)
    
    def truncate(self, a, b=None):
        """Returns a truncated version of the timeseries object"""
        if isinstance(a, TimeRange):
            time_range = a
        else:
            time_range = TimeRange(a,b)
        
        truncated = self.data.truncate(time_range.start(), time_range.end())
        return LightCurve(truncated, self.header.copy())
    
    def extract(self, a):
        """Extract a set of particular columns from the DataFrame"""
        # TODO allow the extract function to pick more than one column
        if isinstance(self, pandas.Series):
            return self
        else:
            return LightCurve(self.data[a], self.header.copy())
        
    def time_range(self):
        """Returns the start and end times of the LightCurve as a TimeRange
        object"""
        return TimeRange(self.data.index[0], self.data.index[-1])

# What's happening here is the following: The ConditionalDispatch is just an
# unbound callable object, that is, it does not know which class it is attached
# to. What we do against that is return a wrapper and make that a classmethod -
# thus we get the class as whose member it is called as as the first argument,
# this is why in the type signature we always have type as the first type.

# We then use run_cls, which just returns a wrapper that interprets the first
# argument as the class the function should be called of. So,
# x = run_cls("foo") returns something that turns x(cls, 1) into cls.foo(1).
# Because this has *args, **kwargs as its signature we need to disable the
# check of ConditionalDispatch that makes sure the function and the
# conditional need to have the same signature - but they still do have to.

LightCurve._cond_dispatch.add(
    run_cls("from_time"),
    lambda cls, time: sunpy.time.is_time(time),
    # type is here because the class parameter is a class,
    # i.e. an instance of type (which is the base meta-class).
    [type, (basestring, datetime, tuple)],
    False
)

LightCurve._cond_dispatch.add(
    run_cls("from_range"),
    lambda cls, time, **kwargs: is_time(time),
    [type, (basestring, datetime, tuple)],
    False
)

LightCurve._cond_dispatch.add(
    run_cls("from_timerange"),
    lambda cls, timerange, **kwargs: True,
    [type, TimeRange],
    False
)

LightCurve._cond_dispatch.add(
    run_cls("from_file"),
    lambda cls, filename: os.path.exists(os.path.expanduser(filename)),
    [type, basestring],
    False
)

LightCurve._cond_dispatch.add(
    run_cls("from_url"),
    lambda cls, url, **kwargs: True,
    [type, basestring],
    False
)

LightCurve._cond_dispatch.add(
    run_cls("from_data"),
    lambda cls, data, index=None, header=None: True,
    [type, (list, dict, np.ndarray, pandas.Series), object, object],
    False
)

LightCurve._cond_dispatch.add(
    run_cls("from_dataframe"),
    lambda cls, dataframe, header=None: True,
    [type, pandas.DataFrame, object],
    False
)

LightCurve._cond_dispatch.add(
    run_cls("from_yesterday"),
    lambda cls: True,
    [type],
    False
)
