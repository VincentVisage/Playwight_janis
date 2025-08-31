from pathlib import Path


def split_login_marketplace(dir_name):

    last_underscore_index = dir_name.rfind('_')

    login = dir_name[:last_underscore_index]
    marketplace = dir_name[last_underscore_index + 1:]
    
    return {"login": login, "marketplace": marketplace}


def get_accounts():
    
    path = Path('profiles/')
    profiles = [item.name for item in path.iterdir() if item.is_dir()]

    accounts = []
    for profile in profiles:
        accounts.append(split_login_marketplace(profile))

    return accounts
