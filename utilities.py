import time

def active_sleep(seconds):
    starttime = time.time()

    while time.time() - starttime < seconds:
        time.sleep(1)

# Возвращает вот такую строку: ?, ?, ?...
def values_placeholder(count):
    return ",".join("?" for i in range(count))

# Возвращает вот такую строку: field1 = ?, field2 = ?, ...
def update_set_placeholder(fields):
    return ",".join(f"{f} = ?" for (f,) in fields)

# Перечисляет все поля через запятую: field1, field2, fields3, ...
def string_of_fields(fields):
    return ",".join(f"{x}" for (x, _) in fields)

# Перечисляет все поля с типом через запятую field1 Integer, field2 Text, ...
def string_of_typed_fields(fields):
    return ",".join(f"{x} {y}" for (x, y) in fields)

def set_attributes_with_aliases(self, data, aliases):
    for (f,_) in self.__class__.fields():
        name = aliases[f] if f in aliases else f
        setattr(self, f, data.get(name, 0))

def set_fields_from_dictionary(self, fields):
    for (field, value) in fields.items():
        setattr(self, field, value)

def make_index_to_field_table(fields):
    return [key for (key,) in fields]