from migrar_sqlite_a_mariadb import migrar


if __name__ == "__main__":
    result = migrar()
    print("Migracion completada:")
    for key, value in result.items():
        print(f" - {key}: {value}")
