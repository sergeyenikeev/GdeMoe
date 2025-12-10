package com.gdemo.data.model

data class ReceiptImportResponse(
    val receipt_id: String,
    val store: String? = null,
    val purchased_at: String? = null,
    val total: Double? = null,
    val currency: String? = null,
    val items: List<ReceiptItem> = emptyList(),
    val file_url: String? = null,
    val note: String? = null
)

data class ReceiptItem(
    val name: String,
    val price: Double? = null,
    val quantity: Double? = null,
    val total: Double? = null
)
