"""
    A simple call to update standard costs in icsw. Included as an example of use of the SXAPIs
    
    connection string "appserver://psssxe:7182/sxapiappsrv"
    wsdl: http://pssapps8/sxapi/serviceIC.svc.
"""
from __future__ import print_function
import zeep
import csv
import json
import datetime
from lxml import etree

class ICService:
    _mode = 'test'
    _debug = False
    _logfile = ''
    
    def __init__(self, mode = 'test', debug=False):
        self._mode = mode
        self._debug = debug      
        
        if self._mode == 'prod':
            web_srv = 'pssapps8'
        else:
            web_srv = 'pssapps12'

        wsdl = 'http://'+web_srv+'/sxapi/ServiceIC.svc?wsdl'    #pull in the WSDL
        client = zeep.Client(wsdl=wsdl)
        self._client = client
        #item_import(file)

    def create_credentials(self, credentials):
        """
        Create the credentials file for use in API calls
        Input:
            -credentials, a dictionary containing three items, which are used in 
            creating the connection:
                -cono: the SXe Company Number in the callConnection object
                -username: the initials of the SXe operator making the call
                -password: the password of the SXe operating making the call 
            -file, a file-like object containing a table mapping to the data needed 
            for sxapiICProductMnt
        Output: A dictionary containing four items:
            -CompanyNumber: the SXe Company Number in the callConnection object
            -ConnectionString: the connection string to the SXAPI server
            -OperatorInitials: the initials of the SXe operator making the call
            -OperatorPassword: the password of the SXe operating making the call 
        """

        #connection_info = {'CompanyNumber':1,'ConnectionString':appsrv_cnxn_str,'OperatorInitials':'atst','OperatorPassword':'\A3F7c?K23E^'}  
        if self._mode == 'prod':
            appsrv_cnxn_str = 'appserver://psssxe:7182/sxapiappsrv'
        else:
            appsrv_cnxn_str = 'appserver://psssxe:7982/test10sxapiappsrv'

        connection_info = {'CompanyNumber':credentials['cono'],
            'ConnectionString':appsrv_cnxn_str,
            'OperatorInitials':credentials['username'],
            'OperatorPassword':credentials['password']}
        return connection_info

    def check_product(self, connection_info, product):
        request={ 'ProductCode':product }
        if self._debug and self._logfile != '':
            with open(self._logfile, 'a') as logf:

                logf.write(etree.tostring(self._client.create_message(
                    self._client.service, 
                    'ICGetProductListV2', 
                    callConnection=connection_info, 
                    request=request)))

                logf.write('\n')
        
        response = self._client.service.ICGetProductListV2(
            callConnection=connection_info, 
            request=request)

        response_dict = zeep.helpers.serialize_object(response)

        if response_dict['Outproduct'] is not None:
            return True
        return False
        #return response_dict

    def check_product_warehouse(self, connection_info, product, warehouse):
        request={ 'Product':product,'Whse':warehouse }
        if self._debug and self._logfile != '':
            with open(self._logfile, 'a') as logf:

                logf.write(etree.tostring(self._client.create_message(
                    self._client.service, 
                    'ICGetWhseProductDataGeneral', 
                    callConnection=connection_info, 
                    request=request)))

                logf.write('\n')

        response = self._client.service.ICGetWhseProductDataGeneral(
            callConnection=connection_info, 
            request=request)

        response_dict = zeep.helpers.serialize_object(response)
        #return response_dict
        if response_dict['ErrorMessage'] is None:
            return True
        return False

    def item_import(self, credentials, file):
        """
        Import items based on file input. Uses the sxapiICProductMnt Call.
        Input:
            -credentials, a dictionary containing three items, which are used in 
            creating the connection:
                -cono: the SXe Company Number in the callConnection object
                -username: the initials of the SXe operator making the call
                -password: the password of the SXe operating making the call 
            -file, a file-like object containing a table mapping to the data needed 
            for sxapiICProductMnt
        Output: A JSON array consisting of two lists: ErrorMessage and ReturnData
        """
        connection_info = self.create_credentials(credentials)

        chg_list = []

        with open(file) as csvfile:
            reader = csv.DictReader(csvfile)
            set_no = 1
            for row in reader:
                seq_no = 1
                key1 = row['prod']
                if 'whse' in row:
                    key2 = row['whse']
                else:
                    key2 = ''
                update_mode = 'chg'
                
                
                if key2 != '':
                    if self.check_product_warehouse(connection_info, key1, key2) == True:
                        update_mode = 'chg'
                    else:
                        update_mode = 'add'
                else:
                    if self.check_product(connection_info, key1) == True:
                        update_mode = 'chg'
                    else:
                        update_mode = 'add'
                
                
                for key in row.keys():
                    if key not in ['prod','whse']:
                        tmp_dict = {}
                        tmp_dict['FieldName'] = key.lower()
                        tmp_dict['FieldValue'] = row[key]
                        tmp_dict['Key1'] = key1
                        tmp_dict['Key2'] = key2
                        tmp_dict['SequenceNumber'] = seq_no
                        tmp_dict['SetNumber'] = set_no
                        tmp_dict['UpdateMode'] = update_mode
                        chg_list.append(tmp_dict)
                        seq_no += 1
                
                set_no += 1
                 

        #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
        request={'InfieldModification':                         
                    {'InfieldModification':
                        chg_list
                    }
                }
        if self._debug and self._logfile != '':
            with open(self._logfile, 'a') as logf:

                logf.write(etree.tostring(self._client.create_message(
                    self._client.service, 
                    'ICProductMnt', 
                    callConnection=connection_info, 
                    request=request)))

                logf.write('\n')
                
        response = self._client.service.ICProductMnt(
            callConnection=connection_info, 
            request=request)    #the actual SOAP call to ICProductMnt

        response_dict = zeep.helpers.serialize_object(response)

        if response_dict['ErrorMessage'] is not None:
            errors = response_dict['ErrorMessage'].split('|')
            response_dict['ErrorMessage'] = errors

        if response_dict['ReturnData'] is not None:
            return_data = response_dict['ReturnData'].split('|')
            response_dict['ReturnData'] = return_data

        #print dir(response)
        if self._logfile != '':
            with open(self._logfile, 'a') as logf:
                print("%s: ICProductMnt - %s" % (datetime.datetime.utcnow(), json.dumps(response_dict)), file=logf)

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

#if __name__ == "__main__":
    #main(mode='test', debug=True)