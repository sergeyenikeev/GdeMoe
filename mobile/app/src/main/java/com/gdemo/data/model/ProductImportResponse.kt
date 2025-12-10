package com.gdemo.data.model

data class ProductImportResponse(
    val title: String? = null,
    val description: String? = null,
    val image_url: String? = null,
    val images: List<String>? = null,
    val attributes: Map<String, String>? = null,
    val price: Double? = null,
    val currency: String? = null,
    val product_url: String? = null,
    val source: String? = null
)
