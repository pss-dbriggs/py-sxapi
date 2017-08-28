"""
    A simple call to update standard costs in icsw. Included as an example of use of the SXAPIs
    
    connection string "appserver://psssxe:7182/sxapiappsrv"
    wsdl: http://pssapps8/sxapi/serviceIC.svc.
"""
from __future__ import print_function
import zeep
import csv
import json
from lxml import etree

_debug = False
_mode = 'test'
_logfile = '/home/dbriggs/environments/sxe_item_import/test.log'

def main(mode = 'test', debug=False):
    _mode = mode
    _debug = debug
    file = '//pssfile2/Users/dbriggs/My Documents/Programming/SXe Item Import/20CPmm3.csv'
    _logfile = '//pssfile2/Users/dbriggs/My Documents/Programming/SXe Item Import/log.txt'
    item_import(file)
    
def item_import(file):
    """
    Input: a file-like object containing a table mapping to the data needed 
        for sxapiICProductMnt
    Output: A JSON array consisting of two lists: ErrorMessage and ReturnData
    """

    logfile=_logfile
    
    if _mode == 'prod':
        web_srv = 'pssapps8'
        appsrv_cnxn_str = 'appserver://psssxe:7182/sxapiappsrv'
    else:
        web_srv = 'pssapps12'
        appsrv_cnxn_str = 'appserver://psssxe:7982/test10sxapiappsrv'

    wsdl = 'http://'+web_srv+'/sxapi/ServiceIC.svc?wsdl'    #pull in the WSDL
    client = zeep.Client(wsdl=wsdl)
    #user credentials, need to be included in every call
    connection_info = {'CompanyNumber':1,'ConnectionString':appsrv_cnxn_str,'OperatorInitials':'atst','OperatorPassword':'\A3F7c?K23E^'}  
        

    chg_list = []

    with open(file) as csvfile:
        reader = csv.DictReader(csvfile)
        set_no = 1
        for row in reader:
            seq_no = 1
            key1 = row['prod']
            key2 = row['whse']
            for key in row.keys():
                if key not in ['prod','whse']:
                    tmp_dict = {}
                    tmp_dict['FieldName'] = key.lower()
                    tmp_dict['FieldValue'] = row[key]
                    tmp_dict['Key1'] = key1
                    tmp_dict['Key2'] = key2
                    tmp_dict['SequenceNumber'] = seq_no
                    tmp_dict['SetNumber'] = set_no
                    tmp_dict['UpdateMode'] = 'chg'
                    chg_list.append(tmp_dict)
                    seq_no += 1
            
            set_no += 1
             

    #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
    request={'InfieldModification':                         
                {'InfieldModification':
                    chg_list
                }
            }
    if _debug and logfile != '':
        with open(logfile, 'a') as logf:
            logf.write(etree.tostring(client.create_message(client.service, 'ICProductMnt', callConnection=connection_info, request=request)))
            logf.write('\n')
            
    response = client.service.ICProductMnt(callConnection=connection_info, request=request)    #the actual SOAP call to ICProductMnt
    response_dict = zeep.helpers.serialize_object(response)

    errors = []
    return_data = []

    errors = response_dict['ErrorMessage'].split('|')
    return_data = response_dict['ReturnData'].split('|')

    response_dict['ErrorMessage'] = errors
    response_dict['ReturnData'] = return_data

    #print dir(response)
    if logfile != '':
        with open(logfile, 'a') as logf:
            print(response_dict, file=logf)

    return json.dumps(response_dict)


    

#ET.tostring(client.create_message(client.service, 'ICProductMnt', callConnection=connection_info, request={}))

"""
request={'InfieldModification':                         #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
            {'InfieldModification':
                [
                    {'FieldName':'stndcost', 'FieldValue':57.05, 'Key1':'AME1715100', 'Key2':'200P', 'SequenceNumber':1, 'SetNumber':1, 'UpdateMode':'chg'},
                    {'FieldName':'stndcost', 'FieldValue':45.03, 'Key1':'AME17093', 'Key2':'200P', 'SequenceNumber':1, 'SetNumber':2, 'UpdateMode':'chg'}
                ]
            }
        }
"""

"""
-Login, use sxe login for authentication?
-Upload Excel file with column headers
    -for each line
        -check all items with blank key2 (icsp only) using sxapiICGetProductListv2 and determine whether they exist
            -if they don't, flag the line as add
            -if they do, flag the line with chg
        -check all items with key2 filled (icsw) using sxapiICGetWhseProductList to determine whether they exist
            -if they don't, flag the line as add
            -if they do, flag the line with chg
-Prepare data for call
    -Allocate a set number for every line in the input file
        -Allocate a sequence for every column in the line
        -

"""

if __name__ == "__main__":
    main(mode='test', debug=True)