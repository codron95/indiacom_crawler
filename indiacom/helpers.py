import yaml

def load_config(stream):
    return yaml.load(stream.read())

def update_config(stream, new_conf):
    stream.seek(0)
    stream.truncate()
    stream.write(yaml.dump(new_conf, default_flow_style=False))
    stream.flush()
