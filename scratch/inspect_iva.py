import os
os.environ["HEADLESS"] = "true"
from cargador_selenium import iniciar_driver, login, navegar_una_sola_vez
from selenium.webdriver.common.by import By

driver = iniciar_driver()
try:
    login(driver)
    navegar_una_sola_vez(driver)
    
    # Encontrar todos los selects dentro de la tabla o fila de agregar productos
    selects = driver.find_elements(By.TAG_NAME, "select")
    inputs = driver.find_elements(By.TAG_NAME, "input")
    
    print("\n--- SELECTS ---")
    for s in selects:
        name = s.get_attribute("name")
        if name and "add" in name.lower():
            print(f"Select Name: {name}")
            for opt in s.find_elements(By.TAG_NAME, "option"):
                print(f"  Option: value='{opt.get_attribute('value')}' text='{opt.text}'")
                
    print("\n--- INPUTS ---")
    for i in inputs:
        name = i.get_attribute("name")
        if name and "add" in name.lower():
            print(f"Input Name: {name}")
            
finally:
    driver.quit()
