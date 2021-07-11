import enum

version = 1.0


class Layer(enum.Enum):
    source, data_type, name, noise_type, noise_model, export_name, noise_attr = range(1, 8)
    db_low = 'db_low'
