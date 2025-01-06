# |-----------------------------------------------------------------------------
# |            This source code is provided under the Apache 2.0 license      --
# |  and is provided AS IS with no warranty or guarantee of fit for purpose.  --
# |                See the project's LICENSE.md for details.                  --
# |           Copyright LSEG 2025. All rights reserved.                       --
# |-----------------------------------------------------------------------------


#!/usr/bin/env python
import sys
import lseg.data as ld
from lseg.data.delivery import omm_stream
import datetime
import time
import json
import base64
import zlib
import binascii

# list to contain the news envelopes
_news_envelopes = []
RIC_CODE = 'MRN_STORY'
DOMAIN = 'NewsTextAnalytics'
SERVICE = 'ELEKTRON_DD'

# Config the encoding for the console
sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

# Retrieve data
# Callback function to display data or status events
def display_event(eventType, event):
    currentTime = datetime.datetime.now().time()
    print("----------------------------------------------------------")
    print(">>> {} event received at {}".format(eventType, currentTime))
    print(json.dumps(event, indent=2))
    if eventType == "Update":
        process_mrn_update(event)
    return

def process_mrn_update(message_json):  
        """Function process Update Message for MRN domain data"""
        fields_data = message_json['Fields']

        # declare variables
        tot_size = 0
        guid = None

        try:
            # Get data for all required fields
            fragment = base64.b64decode(fields_data['FRAGMENT'])
            frag_num = int(fields_data['FRAG_NUM'])
            guid = fields_data['GUID']
            mrn_src = fields_data['MRN_SRC']

            #print("GUID  = %s" % guid)
            #print("FRAG_NUM = %d" % frag_num)
            #print("MRN_SRC = %s" % mrn_src)

            if frag_num > 1:  # We are now processing more than one part of an envelope - retrieve the current details
                guid_index = next((index for (index, d) in enumerate(_news_envelopes) if d['GUID'] == guid), None)
                envelop = _news_envelopes[guid_index]
                if envelop and envelop['data']['MRN_SRC'] == mrn_src and frag_num == envelop['data']['FRAG_NUM'] + 1:
                    print(f'process multiple fragments for guid {envelop["GUID"]}')

                    #print(f'fragment before merge = {len(envelop["data"]["FRAGMENT"])}')
                    # Merge incoming data to existing news envelop and getting FRAGMENT and TOT_SIZE data to local variables
                    fragment = envelop['data']['FRAGMENT'] = envelop['data']['FRAGMENT'] + fragment
                    envelop['data']['FRAG_NUM'] = frag_num
                    tot_size = envelop['data']['tot_size']
                    print(f'TOT_SIZE = {tot_size}')
                    print(f'Current FRAGMENT length = {len(fragment)}')

                    # The multiple fragments news are not completed, waiting.
                    if tot_size != len(fragment):
                        return None
                    # The multiple fragments news are completed, delete associate GUID envelop
                    elif tot_size == len(fragment):
                        del _news_envelopes[guid_index]
                else:
                    print(f'Error: Cannot find fragment for GUID {guid} with matching FRAG_NUM or MRN_SRC {mrn_src}')
                    return None
            else:  # FRAG_NUM = 1 The first fragment
                tot_size = int(fields_data['TOT_SIZE'])
                print(f'FRAGMENT length = {len(fragment)}')
                # The fragment news is not completed, waiting and add this news data to envelop object.
                if tot_size != len(fragment):
                    print(f'Add new fragments to news envelop for guid {guid}')
                    _news_envelopes.append({  # the envelop object is a Python dictionary with GUID as a key and other fields are data
                        'GUID': guid,
                        'data': {
                            'FRAGMENT': fragment,
                            'MRN_SRC': mrn_src,
                            'FRAG_NUM': frag_num,
                            "tot_size": tot_size
                        }
                    })
                    return None

            # News Fragment(s) completed, decompress and print data as JSON to console
            if tot_size == len(fragment):
                print(f'decompress News FRAGMENT(s) for GUID {guid}')
                decompressed_data = zlib.decompress(fragment, zlib.MAX_WBITS | 32)
                print(f'News = {json.loads(decompressed_data)}')

        except KeyError as keyerror:
            print('KeyError exception: ', keyerror)
        except IndexError as indexerror:
            print('IndexError exception: ', indexerror)
        except binascii.Error as b64error:
            print('base64 decoding exception:', b64error)
        except zlib.error as error:
            print('zlib decompressing exception: ', error)
        # Some console environments like Windows may encounter this unicode display as a limitation of OS
        except UnicodeEncodeError as encodeerror:
            print(f'UnicodeEncodeError exception. Cannot decode unicode character for {guid} in this environment: ', encodeerror)
        except Exception as e:
            print('exception: ', sys.exc_info()[0])

if __name__ == '__main__':
    # Open the data session
    ld.open_session()
    #ld.open_session(config_name='./lseg-data.devrel.config.json')

    # Create an OMM stream and register event callbacks
    stream = omm_stream.Definition(
        name = RIC_CODE, 
        domain = DOMAIN,
        service = SERVICE).get_stream()

    # Define the event callbacks
    # Refresh - the first full image we get back from the server
    stream.on_refresh(lambda event, item_stream  : display_event("Refresh", event))

    # Update - as and when field values change, we receive updates from the server
    stream.on_update(lambda event, item_stream : display_event("Update", event))

    # Status - if data goes stale or item closes, we get a status message
    stream.on_status(lambda event, item_stream : display_event("Status", event))

    # Other errors
    stream.on_error(lambda event, item_stream : display_event("Error", event))

    # Open the stream

    # Send request to server and open stream
    stream.open()
    # We should receive the initial Refresh for the current field values
    # followed by updates for the fields as and when they occur

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stream.close()
        # Close the session
        ld.close_session()
