"""
    Wrapper for SXAPI calls
    
    connection string "appserver://psssxe:7182/sxapiappsrv"
    wsdl: http://pssapps8/sxapi/serviceIC.svc.
"""
from __future__ import print_function
import csv
import json
import requests
import datetime
from bs4 import BeautifulSoup

class py_sxapi:
    _mode = 'test'
    _debug = False
    _logfile = '/home/dbriggs/environments/sxe_item_import/test_log.log'
    _endpoint = ''
    _credentials = {}
    _directory = {}
    
    def __init__(self, mode = 'prod', debug=False):
        """
        TODO: Make endpoint and logfile parameters, pull both from config file if not specified
        """
        self._mode = mode
        self._debug = debug  
        
        if self._mode == 'prod':
            self.endpoint = 'http://psssxe2:8185/rest/sxapirestservice/'
        else:
            self.endpoint = 'http://psssxe3:8080/rest/sxapirestservice/'

        #Legacy SOAP code, can remove
        """wsdl = 'http://'+web_srv+'/sxapi/ServiceIC.svc?wsdl'    #pull in the WSDL
        client = zeep.Client(wsdl=wsdl)
        self._client = client"""
        #item_import(file)
    def get_directory(self):
        response = requests.get(self.endpoint+'?_wadl')
        soup = BeautifulSoup(response.text, 'lxml')
        for tag in soup.resources.find_all(path=True):
            self._directory[tag['path'][1:]] = tag.find('method')['name']


    def create_credentials(self, credentials):
        """
        !!!Deprecated due to switch to REST 
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

    def send_request(self, function, data):

        if self._debug and self._logfile != '': #write to log if debug is turned on
            with open(self._logfile, 'a') as logf:

                logf.write(json.dumps(data))
                logf.write('\n')

        response = requests.post(self.endpoint+function, json=data)         
        
        if response.status_code == requests.codes.ok:
            with open(self._logfile, 'a') as logf:
                print(response.text, file=logf)
        
        else:
            with open(self._logfile, 'a') as logf:
                print(response.text, file=logf)
        return response

    def check_product(self, product, credentials=None):
        """
        Checks for the presence of a product. Uses the sxapiicgetproductlistv2 Call.
        Input:
            -credentials, a dictionary containing three items, which are used in 
            creating the connection:
                -cono: the SXe Company Number in the callConnection object
                -username: the initials of the SXe operator making the call
                -password: the password of the SXe operating making the call 
            -product, the product number to check for
        Output: True if the product exists, false if not.
        """
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

        request={'request':                         #the request payload. See ICGetProductListV2 in the SXAPI docs for more information on structure
            {
                'companyNumber': credentials['cono'],
                'operatorInit' : credentials['username'],
                'operatorPassword' : credentials['password'],
                'productCode' : product
            }
        }
        
        #response = self._client.service.ICGetProductListV2( legacy SOAP call
        #    callConnection=connection_info, 
        #    request=request)

        response = self.send_request(function='sxapiicgetproductlistv2', data=request)

        response_dict = response.json()

        l = response_dict['response']['tProdv2']['t-prodv2']
        items = [item['prod'] for item in l]

        if product in items:
            return True
        return False
        #return response_dict

    def check_product_warehouse(self, product, warehouse, credentials=None):
        """
        Checks for the presence of a product in a particular warehouse. Uses the sxapiicgetwhseproductdatageneralv2 Call.
        Input:
            -credentials, a dictionary containing three items, which are used in 
            creating the connection:
                -cono: the SXe Company Number in the callConnection object
                -username: the initials of the SXe operator making the call
                -password: the password of the SXe operating making the call 
            -product, the product number to check for
            -warehouse, the warehouse to look in
        Output: True if the product is present, false if not. Fails on any error other than 'Product/Warehouse Not Set Up'
        """
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

        request={'request':                         #the request payload. See ICGetWhseProductDataGeneral in the SXAPI docs for more information on structure
            {
                'companyNumber': credentials['cono'],
                'operatorInit' : credentials['username'],
                'operatorPassword' : credentials['password'],
                'product':product,
                'whse':warehouse
            }
        }

        response = self.send_request(function='sxapiicgetwhseproductdatageneralv2', data=request)

        response_dict = response.json()

        #return response_dict
        if response_dict['response']['cErrorMessage'] == 'Product/Warehouse Not Set Up in Warehouse Products - ICSW (4602)':
            return False
        elif response_dict['response']['cErrorMessage'] != '':
            raise ValueError('Cannot validate ICSW record')
        else:
            return True

    def item_import(self, file, credentials=None):
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
        #connection_info = self.create_credentials(credentials)
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

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
                    if self.check_product_warehouse(key1, key2, credentials) == True:
                        update_mode = 'chg'
                    else:
                        update_mode = 'add'
                else:
                    if self.check_product(key1, credentials) == True:
                        update_mode = 'chg'
                    else:
                        update_mode = 'add'

                for key in row.keys():
                    if key not in ['prod','whse']:
                        tmp_dict = {}
                        tmp_dict['fieldName'] = key.lower()
                        tmp_dict['fieldValue'] = row[key]
                        tmp_dict['key1'] = key1
                        tmp_dict['key2'] = key2
                        tmp_dict['seqNo'] = seq_no
                        tmp_dict['setNo'] = set_no
                        tmp_dict['updateMode'] = update_mode
                        chg_list.append(tmp_dict)
                        seq_no += 1
                
                set_no += 1
                 

        #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
        request={'request':                         #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
            {
                'companyNumber': credentials['cono'],
                'operatorInit' : credentials['username'],
                'operatorPassword' : credentials['password'],
                'tMntTt' : {'t-mnt-tt':chg_list}
            }
        }
        
        response = self.send_request(function='sxapiicproductmnt', data=request)

        response_dict = response.json()
        return_dict = {}

        if response_dict['response']['cErrorMessage'] is not None:
            errors = response_dict['response']['cErrorMessage'].split('|')
            return_dict['ErrorMessage'] = errors

        if response_dict['response']['returnData'] is not None:
            return_data = response_dict['response']['returnData'].split('|')
            return_dict['ReturnData'] = return_data

        #print dir(response)
        if self._logfile != '':
            with open(self._logfile, 'a') as logf:
                print("%s: ICProductMnt - %s" % (datetime.datetime.utcnow(), json.dumps(return_dict)), file=logf)

        return json.dumps(return_dict)

    def customer_import(self, file, credentials=None):
        """
        Import customer data based on file input. Uses the sxapiARCustomerMnt Call.
        Input:
            -credentials, a dictionary containing three items, which are used in 
            creating the connection:
                -cono: the SXe Company Number in the callConnection object
                -username: the initials of the SXe operator making the call
                -password: the password of the SXe operating making the call 
            -file, a file-like object containing a table mapping to the data needed 
            for sxapiARCustomerMnt
        Output: A JSON array consisting of two lists: ErrorMessage and ReturnData
        """
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

        chg_list = []

        with open(file) as csvfile:
            reader = csv.DictReader(csvfile)
            set_no = 1
            for row in reader:
                seq_no = 1
                key1 = row['custno']
                if 'shipto' in row:
                    key2 = row['shipto']
                else:
                    key2 = ''
                for key in row.keys():
                    if key not in ['custno','shipto']:
                        tmp_dict = {}
                        tmp_dict['fieldName'] = key.lower()
                        tmp_dict['fieldValue'] = row[key]
                        tmp_dict['key1'] = key1
                        tmp_dict['key2'] = key2
                        tmp_dict['seqNo'] = seq_no
                        tmp_dict['setNo'] = set_no
                        tmp_dict['updateMode'] = 'chg'
                        chg_list.append(tmp_dict)
                        seq_no += 1
                
                set_no += 1
                 

        #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
        request={'request':                         #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
            {
                'companyNumber': credentials['cono'],
                'operatorInit' : credentials['username'],
                'operatorPassword' : credentials['password'],
                'tMntTt' : {'t-mnt-tt':chg_list}
            }
        }
        
        response = self.send_request(function='sxapiarcustomermnt', data=request)

        response_dict = response.json()
        return_dict = {}

        if response_dict['response']['cErrorMessage'] is not None:
            errors = response_dict['response']['cErrorMessage'].split('|')
            return_dict['ErrorMessage'] = errors

        if response_dict['response']['returnData'] is not None:
            return_data = response_dict['response']['returnData'].split('|')
            return_dict['ReturnData'] = return_data

        #print dir(response)
        if self._logfile != '':
            with open(self._logfile, 'a') as logf:
                print("%s: ARCustomerMnt - %s" % (datetime.datetime.utcnow(), json.dumps(return_dict)), file=logf)

        return json.dumps(return_dict)