"""
    Wrapper for SXAPI calls
    
    connection string "appserver://psssxe:7182/sxapiappsrv"
    wsdl: http://pssapps8/sxapi/serviceIC.svc.
"""
from __future__ import print_function
import configparser
import csv
import json
from typing import Dict, List, Any

import requests
import datetime
from bs4 import BeautifulSoup


def chunk(length, data):
    """
    Used to separate long lists into multiple requests for performance reasons.
    Input:
        -length, the max length of each chunk to be returned
        -list, the list of elements to be chunked
    Output: List of chunks of max length length
    """
    for i in range(0, len(data), length):
        yield data[i:i + length]


class py_sxapi:
    _mode = 'prod'
    _debug = False
    _logfile = ''
    _endpoint = ''
    _credentials = {}
    _directory = {}
    
    def __init__(self, mode, debug=False):
        """
        TODO: Make endpoint and logfile parameters, pull both (as well as mode) from config file if not specified
        """
        config = configparser.ConfigParser()
        config.read('config.ini')

        if not mode:
            self._mode = config['DEFAULT']['mode']

        self._endpoint = config[self._mode]['endpoint']
        self._debug = config[self._mode].getboolean('debug')

        if self._debug:
            self._logfile = config[self._mode]['logfile']

    def get_directory(self):
        response = requests.get(self._endpoint+'?_wadl')
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

        response = requests.post(self._endpoint+function, json=data)
        
        if response.status_code == requests.codes.ok and self._logfile != '':
            with open(self._logfile, 'a') as logf:
                print(response.text, file=logf)
        
        else:
            if self._logfile != '':
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

        request = {'request':
            {
                'companyNumber': credentials['cono'],
                'operatorInit' : credentials['username'],
                'operatorPassword' : credentials['password'],
                'productCode' : product
            }
        }

        response = self.send_request(function='sxapiicgetproductlistv2', data=request)

        response_dict = response.json()

        l = response_dict['response']['tProdv2']['t-prodv2']
        items = [item['prod'] for item in l]

        if product in items:
            return True
        return False

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

        request={'request':
            {
                'companyNumber': credentials['cono'],
                'operatorInit': credentials['username'],
                'operatorPassword': credentials['password'],
                'product': product,
                'whse': warehouse
            }
        }

        response = self.send_request(function='sxapiicgetwhseproductdatageneralv2', data=request)

        response_dict = response.json()

        if response_dict['response']['cErrorMessage'] == \
                'Product/Warehouse Not Set Up in Warehouse Products - ICSW (4602)':
            return False
        elif response_dict['response']['cErrorMessage'] != '':
            raise ValueError('Cannot validate ICSW record')
        else:
            return True

    def get_product_data(self, product, use_xref=0, credentials=None):
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

        request = {'request':
            {
                'companyNumber': credentials['cono'],
                'operatorInit': credentials['username'],
                'operatorPassword': credentials['password'],
                'productCode': product,
                'useCrossReferenceFlag': use_xref
            }
        }

        response = self.send_request(function='sxapiicgetproductdatageneralv3', data=request)

        response_dict = response.json()

        return response_dict

    def item_import(self, file, credentials=None):
        """
        Import items based on file input. Uses the sxapiICProductMnt Call.
        Input:
            -credentials, a dictionary containing three items, which are used in 
            creating the connection:
                -cono: the SXe Company Number in the callConnection object
                -username: the initials of the SXe operator making the call
                -password: the password of the SXe operating making the call 
            -file, an iterable containing a table mapping to the data needed 
            for sxapiICProductMnt
        Output: A JSON array consisting of two lists: ErrorMessage and ReturnData
        """
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

        chg_list = []

        set_no = 1
        for row in file:
            seq_no = 1
            key1 = row['prod']
            if 'whse' in row:
                key2 = row['whse']
            else:
                key2 = ''
            update_mode = 'chg'
            
            if key2 != '':
                if self.check_product_warehouse(key1, key2, credentials):
                    update_mode = 'chg'
                else:
                    update_mode = 'add'
            else:
                if self.check_product(key1, credentials):
                    update_mode = 'chg'
                else:
                    update_mode = 'add'

            for key in row.keys():
                if key not in ['prod','whse']:
                    tmp_dict = {'fieldName': key.lower(), 'fieldValue': row[key], 'key1': key1, 'key2': key2,
                                'seqNo': seq_no, 'setNo': set_no, 'updateMode': update_mode}
                    chg_list.append(tmp_dict)
                    seq_no += 1
            
            set_no += 1

        chg_batch = list(chunk(100, chg_list))

        return_dict = {'ErrorMessage': [], 'ReturnData': []}

        for batch in chg_batch:
            #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
            request={'request':
                {
                    'companyNumber': credentials['cono'],
                    'operatorInit' : credentials['username'],
                    'operatorPassword' : credentials['password'],
                    'tMntTt' : {'t-mnt-tt':batch}
                }
            }
        
            response = self.send_request(function='sxapiicproductmnt', data=request)

            response_dict = response.json()

            if response_dict['response']['cErrorMessage'] is not None:
                errors = response_dict['response']['cErrorMessage'].split('|')
                for item in errors:
                    return_dict['ErrorMessage'].append(item)

            if response_dict['response']['returnData'] is not None:
                return_data = response_dict['response']['returnData'].split('|')
                for item in return_data:
                    return_dict['ReturnData'].append(item)

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
            -file, an iterable containing a table mapping to the data needed 
            for sxapiARCustomerMnt
        Output: A JSON array consisting of two lists: ErrorMessage and ReturnData
        """
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

        chg_list = []

        set_no = 1
        for row in file:
            seq_no = 1
            key1 = row['custno']
            if 'shipto' in row:
                key2 = row['shipto']
            else:
                key2 = ''
            for key in row.keys():
                if key not in ['custno','shipto']:
                    tmp_dict = {'fieldName': key.lower(), 'fieldValue': row[key], 'key1': key1, 'key2': key2,
                                'seqNo': seq_no, 'setNo': set_no, 'updateMode': 'chg'}
                    chg_list.append(tmp_dict)
                    seq_no += 1
            
            set_no += 1

        request={'request':  #the request payload. See ICProductMnt in the SXAPI docs for more information on structure
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

        if self._logfile != '':
            with open(self._logfile, 'a') as logf:
                print("%s: ARCustomerMnt - %s" % (datetime.datetime.utcnow(), json.dumps(return_dict)), file=logf)

        return json.dumps(return_dict)

    def pricing_import(self, file, credentials=None):
        """
        Import customer data based on file input. Uses the sxapiARCustomerMnt Call.
        Input:
            -credentials, a dictionary containing three items, which are used in
            creating the connection:
                -cono: the SXe Company Number in the callConnection object
                -username: the initials of the SXe operator making the call
                -password: the password of the SXe operating making the call
            -file, an iterable containing a table mapping to the data needed
            for sxapiARCustomerMnt
        Output: A JSON array consisting of two lists: ErrorMessage and ReturnData
        """
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

        chg_list = []

        set_no = 1
        for row in file:
            update_mode = 'chg'
            seq_no = 1
            if 'pdrecno' in row.keys():
                key1 = row['pdrecno']
                if row['pdrecno'] == '':
                    update_mode = 'add'
            else:
                key1 = ''
                update_mode = 'add'
            key2 = ''
            for key in row.keys():
                if key not in ['pdrecno']:
                    tmp_dict = {'fieldName': key.lower(), 'fieldValue': row[key], 'key1': key1, 'key2': key2,
                                'seqNo': seq_no, 'setNo': set_no, 'updateMode': update_mode}
                    chg_list.append(tmp_dict)
                    seq_no += 1

            set_no += 1

        request = {
            'request':  # the request payload. See ICProductMnt in the SXAPI docs for more information on structure
                {
                    'companyNumber': credentials['cono'],
                    'operatorInit': credentials['username'],
                    'operatorPassword': credentials['password'],
                    'tMntTt': {'t-mnt-tt': chg_list}
                }
        }

        response = self.send_request(function='sxapipdpricingmnt', data=request)

        response_dict = response.json()
        return_dict = {}

        if response_dict['response']['cErrorMessage'] is not None:
            errors = response_dict['response']['cErrorMessage'].split('|')
            return_dict['ErrorMessage'] = errors

        if response_dict['response']['returnData'] is not None:
            return_data = response_dict['response']['returnData'].split('|')
            return_dict['ReturnData'] = return_data

        if self._logfile != '':
            with open(self._logfile, 'a') as logf:
                print("%s: ARCustomerMnt - %s" % (datetime.datetime.utcnow(), json.dumps(return_dict)), file=logf)

        return json.dumps(return_dict)

    def get_pricing(self, data, customer_number, ship_to, warehouse, credentials=None):
        """
        Import customer data based on file input. Uses the sxapiARCustomerMnt Call.
        Input:
            -credentials, a dictionary containing three items, which are used in
            creating the connection:
                -cono: the SXe Company Number in the callConnection object
                -username: the initials of the SXe operator making the call
                -password: the password of the SXe operating making the call
            -file, an iterable containing a table mapping to the data needed
            for sxapiARCustomerMnt
        Output: A JSON array consisting of two lists: ErrorMessage and ReturnData
        """
        if credentials is None and self._credentials != {}:
            credentials = self._credentials

        if customer_number == 0:
            customer_number = '10008088'
        if ship_to == '0':
            ship_to = '1'
        if warehouse == '':
            warehouse = '100p'

        return_dict: List[Dict[str, Any]] = []

        for row in data:
            try:
                unit = row['unit']
            except KeyError:
                unit = 'each'

            try:
                qty = row['qty']
            except KeyError:
                qty = 1

            request = {
                'request':  # request payload. See ICProductMnt in the SXAPI docs for more information on structure
                    {
                        'companyNumber': credentials['cono'],
                        'operatorInit': credentials['username'],
                        'operatorPassword': credentials['password'],
                        'customerNumber': customer_number,
                        'shipTo': ship_to,
                        'warehouse': warehouse,
                        'quantity': qty,
                        'productCode': row['prod'],
                        'unitOfMeasure': unit
                    }
            }

            response = self.send_request(function='sxapioepricing', data=request)
            response_dict = response.json()

            return_dict.append({'prod': row['prod'],
                                'price': response_dict['response']['price'],
                                'discount_amount':response_dict['response']['discountAmount'],
                                'discount_type':response_dict['response']['discountType'],
                                'net_available':response_dict['response']['netAvailable']
                                })

        """with open('//pssfile3/Users/dbriggs/My Documents/Pricing/pricing_test_out.csv', 'w') as csvfile:
            fieldnames = ['prod', 'price']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in return_dict:
                writer.writerow(row)"""
        if len(return_dict) == 1:
            return return_dict[0]
        else:
            return return_dict
