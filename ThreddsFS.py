from fs.base import FS
from fs.info import Info
from fs.enums import ResourceType
from fs.errors import ResourceReadOnly, Unsupported
import requests
from lxml import etree
from functools import lru_cache
import os


global namespaces
namespaces = {'thredds': 'http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0'}

class ThreddsFS(FS):
    """A custom class to browse a THREDDS server as a filesystem."""
    def __init__(self, domain_url, base_url, base_catalogs_url, root_catalog_url):
        super().__init__()
        self.domain_url = domain_url
        self.base_url = base_url
        self.base_catalogs_url = base_catalogs_url
        self.root_catalog_url = root_catalog_url

    def retrieve_catalog(self, catalog_url):
        """Retrieve the catalog.xml file from a url"""
        response = requests.get(catalog_url)
        if response.status_code >= 400:
            raise Exception(f"Error {response.status_code} for url {catalog_url}")
        root = etree.fromstring(response.content)
        return root

    def search_catalog_for_ref(self, catalog_url, ref_name):
        """Retrieve the lxml element in a catalog.xml file, if it is not found, throws an Exception"""
        catalog = self.retrieve_catalog(catalog_url)
        
        # Get all catalogRef nodes
        catalog_refs = catalog.findall('.//thredds:catalogRef', namespaces)
        # Compute the node name from the given href and associate it to a catalogRef node
        # Warning: the node name is computed only from leaf element in path. 
        # Example: OSISAF/OSI-201-b-metop_b_FULL_TIME_SERIE.xml => OSI-201-b-metop_b_FULL_TIME_SERIE   
        catalog_ref_dict = {ref.get('{http://www.w3.org/1999/xlink}href')
                            .replace('/catalog.xml', '')                    # /catalog.xml is present when catalogRef is type DatasetScan
                            .rsplit('/', 1)[-1]                             
                            .replace('.xml', '')
                            : ref for ref in catalog_refs}
        matching_refs = {name: ref for (name, ref) in catalog_ref_dict.items() if name == ref_name}
        try:
            catalog_ref = list(matching_refs.values()).pop()
        except IndexError:
            raise Exception(f"No matching {ref_name} in {catalog_url}.\nChoose in {catalog_ref_dict.keys()}")
        return catalog_ref
            
    def build_catalog_url(self, catalog_ref, parent_catalog_url=None):
        """Building catalog_url depending on the nature of catalog_ref"""
        href = catalog_ref.get('{http://www.w3.org/1999/xlink}href')
        
        # Retrieve properties
        is_dataset_scan = True if href.endswith('catalog.xml') else False
        if is_dataset_scan:
            #'DatasetScan' property is only present for root element of datasetScan
            is_root_dataset_scan = False
            dataset_scan_prop = catalog_ref.xpath(".//thredds:property[@name='DatasetScan']",namespaces=namespaces)
            if dataset_scan_prop: 
                is_root_dataset_scan = True if dataset_scan_prop[0].get("value") == 'true' else False
        
        # Compute url depending on cases
        if is_dataset_scan:
            if is_root_dataset_scan:
                catalog_url = self.domain_url + href
            else:
                catalog_url = os.path.join(parent_catalog_url.replace('catalog.xml', ''), href)
        else:
            if href.startswith('catalogs/'):
                catalog_url = self.base_url + href
            else: 
                catalog_url = self.base_catalogs_url + href
        return catalog_url

    # @lru_cache(maxsize=1024)
    # def get_url_from_path(self, path):
    #     """Non recursive version"""    
    #     splitted_path = list(filter(lambda x: x!='', path.strip('/').split('/')))
    #     catalog_url = self.root_catalog_url

    #     for i in range(0 , len(splitted_path)):
    #         ref_name = splitted_path[i]

    #         catalog_ref = self.search_catalog_for_ref(catalog_url, ref_name)
    #         catalog_url = self.build_catalog_url(catalog_ref)
                
    #     return catalog_url

    @lru_cache(maxsize=1024)
    def get_url_from_path(self, path):
        """
        Get a real Thredds URL from an emulated Python path.
        Recursive function with cache associating input to output, so the function acts as a dict(path => url)
        """
        if path == '/' or path == '':
            catalog_url = self.root_catalog_url
        else :
            splitted_path = list(filter(lambda x: x!='', path.strip('/').split('/')))

            ref_name = splitted_path[-1]
            parent_path = os.path.join('/', *splitted_path[:-1])
            parent_catalog_url =  self.get_url_from_path(parent_path)

            catalog_ref = self.search_catalog_for_ref(parent_catalog_url, ref_name)
            catalog_url = self.build_catalog_url(catalog_ref, parent_catalog_url)
        return catalog_url


    def listdir(self, path):
        """List the contents of a THREDDS catalog."""
        
        catalog_url = self.get_url_from_path(path)
        root = self.retrieve_catalog(catalog_url)

        contents = []
        for dataset in root.findall('.//thredds:dataset', namespaces):
            contents.append(dataset.get('name'))
        for catalog_ref in root.findall('.//thredds:catalogRef', namespaces):
            contents.append(catalog_ref.get('{http://www.w3.org/1999/xlink}title'))
        return contents

    def getinfo(self, path, namespaces=None):
        """Get information about a file or directory."""
        if path == '/':
            return Info({
                'basic': {
                    'name': '/',
                    'is_dir': True
                }
            })
        else:
            return Info({
                'basic': {
                    'name': path.split('/')[-1],
                    'is_dir': True  # Assume everything is a directory for simplicity
                }
            })

    def openbin(self, path, mode='r', buffering=-1, **kwargs):
        """Open a file in binary mode."""
        if 'w' in mode or 'a' in mode or '+' in mode:
            raise ResourceReadOnly("The THREDDS filesystem is read-only.")
        # Implement logic to access files via HTTPServer or OPENDAP
        raise Unsupported("Access to binary files is not implemented in this example.")

    def makedir(self, path, permissions=None, recreate=False):
        """Create a directory."""
        raise ResourceReadOnly("The THREDDS filesystem is read-only.")

    def remove(self, path):
        """Remove a file."""
        raise ResourceReadOnly("The THREDDS filesystem is read-only.")

    def removedir(self, path):
        """Remove a directory."""
        raise ResourceReadOnly("The THREDDS filesystem is read-only.")

    def setinfo(self, path, info):
        """Set information about a file or directory."""
        raise ResourceReadOnly("The THREDDS filesystem is read-only.")

domain_url = 'https://tds0.ifremer.fr/'
base_url = os.path.join(domain_url, 'thredds/')
base_catalogs_url = os.path.join(base_url, 'catalogs/')
root_catalog_url = os.path.join(base_url, 'catalog.xml')

# Example usage
thredds_fs = ThreddsFS(domain_url, base_url, base_catalogs_url, root_catalog_url)

# List the contents of the root directory
print("Root directory contents:", thredds_fs.listdir('/'))

# List the contents of a subdirectory
subdirectory = '/CERSAT/OSISAF'
print(f"Contents of {subdirectory}:", thredds_fs.listdir(subdirectory))

subdirectory = '/CERSAT/OSISAF/OSI-IO-DLI-SSI-hourly-series'
print(f"Contents of {subdirectory}:", thredds_fs.listdir(subdirectory))

subdirectory = '/CERSAT/OSISAF/OSI-305-306-daily-series/2016'
print(f"Contents of {subdirectory}:", thredds_fs.listdir(subdirectory))

subdirectory = '/CERSAT/OSISAF/OSI-305-306-daily-series/2016/358'
print(f"Contents of {subdirectory}:", thredds_fs.listdir(subdirectory))
