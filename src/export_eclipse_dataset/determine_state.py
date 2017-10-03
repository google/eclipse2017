from functools import partial
import pickle
import argparse
import googlemaps
from multiprocessing import Pool

def get_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--filtered_photo_metadata', type=str, default="filtered_photo_metadata.pkl")
    parser.add_argument('--google_maps_api_key', type=str)
    parser.add_argument('--state_output', type=str, default="states.pkl")
    return parser.parse_args()

def get_state(gmaps, item):
    lat = item['lat']
    lng = -item['lon']
    try:
        reverse_geocode_result = gmaps.reverse_geocode((lat, lng))
    except googlemaps.exceptions.Timeout:
        return item.key.name, None
    for result in reverse_geocode_result:
        for address_component in result['address_components']:
            if u'administrative_area_level_1' in address_component['types'] :
                state = address_component['short_name']
                return item.key.name, state
    return item.key.name, None
    
def main():
    args = get_arguments()

    TIMEOUT=30
    RETRY_TIMEOUT=30
    gmaps = googlemaps.Client(key=args.google_maps_api_key,
                              timeout=TIMEOUT,
                              retry_timeout=RETRY_TIMEOUT)
    # Load photo points
    r = pickle.load(open(args.filtered_photo_metadata))
    f = partial(get_state, gmaps)
    p = Pool(5)
    results = p.map(f, r)
    pickle.dump(dict(results), open(args.state_output, "wb"))
            
if __name__ == '__main__':
    main()
