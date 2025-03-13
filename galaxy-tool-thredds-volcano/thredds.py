
import argparse
import os
from owslib import wcs
import netCDF4 as nc

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')

def get_data(url_cat, file, id_ds, lat_min, lat_max, lon_min, lon_max):
    wcs_thredds = url_cat.split('catalog')[0] + 'wcs/'
    _wcs = wcs.WebCoverageService(f"{wcs_thredds}{file}", version='1.0.0')
    mychunk = _wcs.getCoverage(identifier=id_ds,bbox=(lon_min,lat_min,lon_max,lat_max),format='NetCDF3')
    
    
    filename = os.path.join(OUTPUT_DIR, os.path.basename(file))
    toexclude = []
            
    with nc.Dataset('inmem.nc', memory = mychunk.read()) as src, nc.Dataset(filename, "w", format="NETCDF3_CLASSIC") as dst:
        # copy global attributes all at once via dictionary
        dst.setncatts(src.__dict__)
        # copy dimensions
        for name, dimension in src.dimensions.items():
            dst.createDimension(
                name, (len(dimension) if not dimension.isunlimited() else None))
        # copy all file data except for the excluded
        for name, variable in src.variables.items():
            if name not in toexclude:
                dst[name][:] = src[name][:]
                # copy variable attributes all at once via dictionary
                dst[name].setncatts(src[name].__dict__)

    os.system(f"cat {filename}")
    os.remove(filename)

if __name__ == '__main__':
    # get args
    parser = argparse.ArgumentParser(description='Get data from THREDDS server')
    # add optional arguments
    parser.add_argument('--url', help='URL of THREDDS server catalog', default=None)
    parser.add_argument('--file', help='ds file', default=None)
    parser.add_argument('--ds', help='id Dataset', default=None)
    parser.add_argument('--lat_min', help='Minimum latitude', default=None)
    parser.add_argument('--lat_max', help='Maximum latitude', default=None)
    parser.add_argument('--lon_min', help='Minimum longitude', default=None)
    parser.add_argument('--lon_max', help='Maximum longitude', default=None)
    
    args = parser.parse_args()
    
    # get data
    fname = get_data(args.url, args.file, args.ds, args.lat_min, args.lat_max, args.lon_min, args.lon_max)
    print(fname)
    