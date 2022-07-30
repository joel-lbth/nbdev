# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/11_clean.ipynb.

# %% auto 0
__all__ = ['nbdev_trust', 'clean_nb', 'process_write', 'nbdev_clean', 'nbdev_install_hooks', 'clean_jupyter',
           'nbdev_install_jupyter_hooks']

# %% ../nbs/11_clean.ipynb 2
import warnings,stat

from execnb.nbio import *
from fastcore.script import *
from fastcore.basics import *
from fastcore.imports import *

from .imports import *
from .read import *
from .sync import *
from .process import first_code_ln

# %% ../nbs/11_clean.ipynb 5
@call_parse
def nbdev_trust(
    fname:str=None,  # A notebook name or glob to trust
    force_all:bool=False  # Also trust notebooks that haven't changed
):
    "Trust notebooks matching `fname`"
    try: from nbformat.sign import NotebookNotary
    except:
        import warnings
        warnings.warn("Please install jupyter and try again")
        return

    fname = Path(fname if fname else config_key("nbs_path", '.'))
    path = fname if fname.is_dir() else fname.parent
    check_fname = path/".last_checked"
    last_checked = os.path.getmtime(check_fname) if check_fname.exists() else None
    nbs = globtastic(fname, file_glob='*.ipynb', skip_folder_re='^[_.]') if fname.is_dir() else [fname]
    for fn in nbs:
        if last_checked and not force_all:
            last_changed = os.path.getmtime(fn)
            if last_changed < last_checked: continue
        nb = read_nb(fn)
        if not NotebookNotary().check_signature(nb): NotebookNotary().sign(nb)
    check_fname.touch(exist_ok=True)

# %% ../nbs/11_clean.ipynb 7
def _clean_cell_output(cell):
    "Remove execution count in `cell`"
    if 'outputs' in cell:
        for o in cell['outputs']:
            if 'execution_count' in o: o['execution_count'] = None
            o.get('data',{}).pop("application/vnd.google.colaboratory.intrinsic+json", None)
            o.get('metadata', {}).pop('tags', None)

# %% ../nbs/11_clean.ipynb 8
def _clean_cell(cell, clear_all=False, allowed_metadata_keys=None):
    "Clean `cell` by removing superfluous metadata or everything except the input if `clear_all`"
    if 'execution_count' in cell: cell['execution_count'] = None
    if 'outputs' in cell:
        if clear_all: cell['outputs'] = []
        else:         _clean_cell_output(cell)
    if cell['source'] == ['']: cell['source'] = []
    cell['metadata'] = {} if clear_all else {
        k:v for k,v in cell['metadata'].items() if k in allowed_metadata_keys}

# %% ../nbs/11_clean.ipynb 9
def clean_nb(
    nb, # The notebook to clean
    clear_all=False, # Remove all cell metadata and cell outputs
    allowed_metadata_keys:list=None, # Preserve the list of keys in the main notebook metadata
    allowed_cell_metadata_keys:list=None # Preserve the list of keys in cell level metadata
):
    "Clean `nb` from superfluous metadata"
    metadata_keys = {"kernelspec", "jekyll", "jupytext", "doc"}
    if allowed_metadata_keys: metadata_keys.update(allowed_metadata_keys)
    cell_metadata_keys = {"hide_input"}
    if allowed_cell_metadata_keys: cell_metadata_keys.update(allowed_cell_metadata_keys)
    for c in nb['cells']: _clean_cell(c, clear_all=clear_all, allowed_metadata_keys=cell_metadata_keys)
    nb['metadata'] = {k:v for k,v in nb['metadata'].items() if k in metadata_keys}

# %% ../nbs/11_clean.ipynb 19
def _reconfigure(*strms):
    for s in strms:
        if hasattr(s,'reconfigure'): s.reconfigure(encoding='utf-8')

# %% ../nbs/11_clean.ipynb 20
def process_write(warn_msg, proc_nb, f_in, f_out=None, disp=False):
    if not f_out: f_out = sys.stdout if disp else f_in
    if isinstance(f_in, (str,Path)): f_in = Path(f_in).open()
    try:
        _reconfigure(f_in, f_out)
        nb = loads(f_in.read())
        proc_nb(nb)
        write_nb(nb, f_out)
    except Exception as e:
        warn(f'{warn_msg}')
        warn(e)

# %% ../nbs/11_clean.ipynb 21
def _nbdev_clean(nb, **kwargs):
    allowed_metadata_keys = config_key("allowed_metadata_keys", '', missing_ok=True, path=False).split()
    allowed_cell_metadata_keys = config_key("allowed_cell_metadata_keys", '', missing_ok=True, path=False).split()
    return clean_nb(nb, allowed_metadata_keys=allowed_metadata_keys,
                    allowed_cell_metadata_keys=allowed_cell_metadata_keys, **kwargs)

# %% ../nbs/11_clean.ipynb 22
@call_parse
def nbdev_clean(
    fname:str=None, # A notebook name or glob to clean
    clear_all:bool=False, # Clean all metadata and outputs
    disp:bool=False,  # Print the cleaned outputs
    stdin:bool=False # Read notebook from input stream
):
    "Clean all notebooks in `fname` to avoid merge conflicts"
    # Git hooks will pass the notebooks in stdin
    _clean = partial(_nbdev_clean, clear_all=clear_all)
    _write = partial(process_write, warn_msg='Failed to clean notebook', proc_nb=_clean)
    if stdin: return _write(f_in=sys.stdin, f_out=sys.stdout)
    
    if fname is None: fname = config_key("nbs_path", '.', missing_ok=True)
    for f in globtastic(fname, file_glob='*.ipynb', skip_folder_re='^[_.]'): _write(f_in=f, disp=disp)

# %% ../nbs/11_clean.ipynb 24
@call_parse
def nbdev_install_hooks():
    "Install git hooks to clean and trust notebooks automatically"
    nb_path = config_key("nbs_path", '.')
    path = get_config().config_path
    hook_path = path/'.git'/'hooks'
    fn = hook_path/'post-merge'
    hook_path.mkdir(parents=True, exist_ok=True)
    fn.write_text("#!/bin/bash\nnbdev_trust")
    os.chmod(fn, os.stat(fn).st_mode | stat.S_IEXEC)
    #Clean notebooks on commit/diff
    (path/'.gitconfig').write_text("""# Generated by nbdev_install_hooks
#
# If you need to disable this instrumentation do:
#   git config --local --unset include.path
#
# To restore the filter
#   git config --local include.path .gitconfig
#
# If you see notebooks not stripped, checked the filters are applied in .gitattributes
#
[filter "clean-nbs"]
        clean = nbdev_clean --stdin
        smudge = cat
        required = true
[diff "ipynb"]
        textconv = nbdev_clean --disp --fname
""")
    cmd = "git config --local include.path ../.gitconfig"
    run(cmd)
    print("Hooks are installed and repo's .gitconfig is now trusted")
    (nb_path/'.gitattributes').write_text("**/*.ipynb filter=clean-nbs\n**/*.ipynb diff=ipynb\n")

# %% ../nbs/11_clean.ipynb 25
def clean_jupyter(path, model, **kwargs):
    "Clean Jupyter `model` pre save to `path`"
    get_config.cache_clear() # Reset Jupyter's cache
    try: cfg = get_config(path=path)
    except FileNotFoundError: return
    in_nbdev_repo = 'nbs_path' in cfg
    jupyter_hooks = str2bool(cfg.get('jupyter_hooks', True))
    is_nb_v4 = (model['type'],model['content']['nbformat']) == ('notebook',4)
    if in_nbdev_repo and jupyter_hooks and is_nb_v4: _nbdev_clean(model['content'])

# %% ../nbs/11_clean.ipynb 27
def _nested_setdefault(o, attr, default):
    "Same as `setdefault`, but if `attr` includes a `.`, then looks inside nested objects"
    attrs = attr.split('.')
    for a in attrs[:-1]: o = o.setdefault(a, type(o)())
    return o.setdefault(attrs[-1], default)

# %% ../nbs/11_clean.ipynb 31
@call_parse
def nbdev_install_jupyter_hooks():
    "Install Jupyter hooks to clean notebooks on save"
    cfg_path = Path.home()/'.jupyter'
    cfg_fns = [cfg_path/f'jupyter_{o}_config.json' for o in ('notebook','server')]
    attr,hook = 'ContentsManager.pre_save_hook','nbdev.clean.clean_jupyter'
    for fn in cfg_fns:
        cfg = dict2obj(fn.read_json() if fn.exists() else {})
        val = nested_attr(cfg, attr)
        if val is None:
            _nested_setdefault(cfg, attr, hook)
            fn.write_text(dumps(obj2dict(cfg), indent=2))
        elif val != hook:
            sys.stderr.write(f"Can't install hook to '{p}' since it already contains `{attr} = '{val}'`. "
                             f"Manually update to `{attr} = '{hook}'` for this functionality.")
