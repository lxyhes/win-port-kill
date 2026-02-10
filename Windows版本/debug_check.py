try:
    import port_manager
    print("导入成功，语法检查通过")
except Exception as e:
    import traceback
    traceback.print_exc()
