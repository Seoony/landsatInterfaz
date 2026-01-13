def calcular_indice(img, nombre):

    if nombre == "NDVI":
        return img.normalizedDifference(["NIR", "RED"])

    if nombre == "SAVI":
        return img.expression(
            "(NIR - RED) / (NIR + RED + 0.5) * 1.5",
            {"NIR": img.select("NIR"), "RED": img.select("RED")}
        )

    if nombre == "EVI":
        return img.expression(
            "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
            {
                "NIR": img.select("NIR"),
                "RED": img.select("RED"),
                "BLUE": img.select("BLUE")
            }
        )

    if nombre == "GNDVI":
        return img.normalizedDifference(["NIR", "GREEN"])

    if nombre == "LSWI":
        return img.normalizedDifference(["NIR", "SWIR1"])

    if nombre == "NDWI":
        return img.normalizedDifference(["GREEN", "NIR"])

    if nombre == "MNDWI":
        return img.normalizedDifference(["GREEN", "SWIR1"])

    raise ValueError(f"Índice no soportado: {nombre}")
