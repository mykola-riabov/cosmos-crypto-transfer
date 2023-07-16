import sys

# Получение списка директорий, в которых Python ищет модули по умолчанию
default_paths = sys.path

# Вывод списка директорий
for path in default_paths:
    print(path)
