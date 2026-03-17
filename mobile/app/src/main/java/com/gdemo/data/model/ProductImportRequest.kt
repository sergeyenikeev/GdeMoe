package com.gdemo.data.model

data class ProductImportRequest(
    val url: String,
    val source: String? = "mobile_share"
)
