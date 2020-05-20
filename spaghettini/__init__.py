__version__ = "0.0.7"

import oyaml as yaml
import types
from .template import expand
import traceback
from pprint import pprint
import functools
from reprlib import repr
import inspect

MODULES = {}


def check():
    return {
        "num_modules": len(MODULES),
        "keys": list(MODULES)
    }


def check_registered():
    print("################################################################")
    print("Printing registered modules: ")
    for module_key, module in sorted(MODULES.items(), key=lambda kv: kv[0]):
        print(f"{module_key:24}{module}")
    print("################################################################")


def quick_register(module):
    name = module.__name__
    if name in MODULES:
        try:
            is_same_module = inspect.getsourcefile(module) == inspect.getsourcefile(MODULES[name])
        except:
            print("Make sure module {} is not being overloaded!".format(name))
            is_same_module = module.__dict__.keys() == MODULES[name].__dict__.keys()
        if is_same_module:
            print("The module {} is already registered. ".format(name))
        else:
            print("A different module with name {} is already registered. ".format(name))
            print(f"Module repr is {MODULES[name].__repr__}")
            raise NameError
    try:
        MODULES[name] = module
    except Exception as e:
        print("Exception: \n{}".format(e))
        print("Traceback: \n{}".format(traceback.print_exc()))
        print("Message: Couldn't find module named {} to load".format(name))

    return module


def register(name=None):
    assert name not in MODULES, "The module with {} is already registered. ".format(name)
    names = [name]

    def core(module):
        name = names[0]
        if name is None:
            name = module.__name__
        MODULES[name] = module
        return module

    return core


def get(name):
    try:
        return MODULES[name]
    except Exception as e:
        print("\nSpaghettini Message: Module '{}' not registered. \n".format(name))
        raise


def configure(d, record_config=False, verbose=False):
    if type(d) == dict:
        # Strip off the hparam string from the key, if it exists.
        cleaned_d = dict()
        for key, value in d.items():
            if _contains_hparam_key(key):
                key = _strip_off_hparam_key(key)
            cleaned_d[key] = value
        d = cleaned_d

        new_d = {}
        for key, value in d.items():
            if key.startswith("[") and key.endswith("]"):
                for k, v in value.items():
                    assert k not in new_d
                    new_d[k] = v
            else:
                new_d[key] = value
        d = new_d

        assert "<type>" in d, d
        m = get(d["<type>"])

        def core(*args, **kwargs):
            configure_fn = functools.partial(configure, record_config=record_config, verbose=verbose)
            extra_kwargs = {k: configure_fn(d[k]) for k in filter(lambda x:
                                                                  (not x.endswith(">") and not x.startswith("<")), d)}
            if "<list>" in d:
                extra_args = tuple(map(configure_fn, d["<list>"]))
            else:
                extra_args = tuple()
            try:
                v = m(*args, *extra_args, **kwargs, **extra_kwargs)
            except Exception as e:
                print(e)
                print("\nException occured while loading {}.\n".format(d["<type>"]))
                raise

            if record_config:
                v.__config__ = d
            if verbose:
                print(">>>>  Instantiating module: {}".format(m))
                print("Arguments:")
                for i, arg in enumerate(tuple(args + extra_args)):
                    print("\tArgument {}: {}".format(i, arg))
                print("Keyword arguments:")
                for curr_key, curr_value in sorted(dict(**kwargs, **extra_kwargs).items(), key=lambda kv: kv[0]):
                    print("\tKey: {}\n\t\t Value: {}".format(curr_key, repr(curr_value)))
                print("<<<<")
            return v

        if "<init>" in d and d["<init>"]:
            return core()
        return core
    if type(d) == list:
        return list(map(configure, d))
    return d


def gather_hparams_from_config(d, hparams_dict):
    # Note: overrides hparams_dict by aliasing.
    assert isinstance(hparams_dict, dict)

    # Check if non-leaf.
    if isinstance(d, dict):
        # Check if children has hparameter arguments.
        for k, v in d.items():
            if isinstance(k, str) and _contains_hparam_key(k):
                assert isinstance(v, (float, int, str)), f"Hparameters can only be int, float or str. " \
                                                         f"The current one, corresponding to key {k} is {type(v)}. "
                hparam_key = _get_hparam_key(k)
                hparams_dict[hparam_key] = v

            # Recurse.
            gather_hparams_from_config(v, hparams_dict)
    if isinstance(d, list):
        for leaf_d in d:
            gather_hparams_from_config(leaf_d, hparams_dict)


def _contains_hparam_key(key: str):
    check_1 = key.count("(") == 1 and key.count(")") == 1
    check_2 = key.find("(") < key.find(")")
    return check_1 and check_2


def _get_hparam_key(key: str):
    idx1, idx2 = key.find("(") + 1, key.find(")")

    return key[idx1:idx2]


def _strip_off_hparam_key(key: str):
    idx1, idx2 = key.find("("), key.find(")") + 1
    return key[:idx1] + key[idx2:]


def load(path, gather_hparams=False, verbose=False, record_config=True):
    if path.endswith("yaml"):
        with open(path, "r") as f:
            x = yaml.safe_load(f)
        if verbose:
            print(">>>>>>>>  Configuring from '{}'. ".format(path))

        # Configure the modules.
        configured = configure(x, record_config=record_config, verbose=verbose)

        # Gather the hyperparameters, if asked.
        hparams_dict = dict()
        if gather_hparams:
            gather_hparams_from_config(x, hparams_dict)

        # Return.
        return configured if not gather_hparams else (configured, hparams_dict)

    return None


def clear_registered_modules():
    print("This function is not debugged yet.  ")
    MODULES = dict()


