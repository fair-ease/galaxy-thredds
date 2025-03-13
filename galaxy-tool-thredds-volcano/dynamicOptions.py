#import threddsclient
#import owslib.wcs

from galaxy.tools.parameters.basic import DrillDownSelectToolParameter

from galaxy.util import XML


def get_subcats(endpoint_thredds, curr_cat):
    with open('log.txt', 'a') as f:
        f.write(f'start curr_cat: {curr_cat}\n')
    # Get the THREDDS catalog
    if curr_cat is None or curr_cat == '..' or curr_cat == '':
        url = endpoint_thredds
        options = [("", "", True)]
    else:
        url = curr_cat
        options = [("..", "..", False), ("", "", True)]
    
    cat = threddsclient.read_url(url)
    # Get the sub catalog
    subcat = cat.references
    if len(subcat) == 0 and len(cat.datasets) == 1:
        subcat = cat.datasets[0].references
            
    # Create the options list    
    for d in subcat:
        options.append((d.name, d.url, False))
        
    # open a file and read log
    with open('log.txt', 'a') as f:
        f.write(f'end curr_cat: {curr_cat}\n')
            
    return options

def get_file(endpoint_thredds, curr_cat):
    if curr_cat is None or curr_cat == '..':
        url = endpoint_thredds
    else:
        url = curr_cat
    # Get the THREDDS catalog
    cat = threddsclient.read_url(url)
    # Get the datasets
    ds = cat.datasets
    subcat = cat.references
    if len(subcat) == 0 and len(ds) == 1:
        ds = cat.datasets[0].datasets
        
    ds.sort(key=lambda x: x.name)
    # Create the options list
    options = []
    for i, d in enumerate(ds):
        if d.name != 'latest.xml':
            options.append((d.name, d.url_path, i==0))
            
    return options

def get_ds(endpoint_thredds, curr_cat, filename):
    if curr_cat is None or curr_cat == '..':
        url = endpoint_thredds
    else:
        url = curr_cat

    wcs_thredds = url.split('catalog')[0] + 'wcs/'
    wcs = owslib.wcs.WebCoverageService(f'{wcs_thredds}{filename}')
    ids_ds = list(wcs.contents.keys())
    
    options = []
    for i, id in enumerate(ids_ds):
        options.append((id, id, i==0))
        
    return options


def test_drilldown():
    # options = dict(options=[dict(name="aa", value="aa", selected=False), dict(name="bb", value="bb", selected=False)], selected=False)
    options = [("aa", "aa", False), ("bb", "bb", False)]
    p = DrillDownSelectToolParameter(None, XML(
        '''
        <param name="_name" type="drill_down" display="checkbox" hierarchy="recurse" multiple="true">
          <options>
           <option name="Heading 1" value="heading1">
               <option name="Option 1" value="option1"/>
               <option name="Option 2" value="option2"/>
               <option name="Heading 2" value="heading2">
                 <option name="Option 3" value="option3"/>
                 <option name="Option 4" value="option4"/>
               </option>
           </option>
           <option name="Option 5" value="option5"/>
          </options>
        </param>
        '''))
    return p.to_dict()
