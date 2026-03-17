package com.gdemo.data.model

data class CreateItemRequest(
    val title: String,
    val status: String,
    val workspace_id: Int = 2,
    val description: String? = null,
    val category: String? = null,
    val location_id: Int? = null,
    val scope: String = "private",
    val tags: List<String> = emptyList(),
    val attributes: Map<String, Any?>? = null,
    val links: List<String>? = null,
    val purchase_date: String? = null,
    val purchase_datetime: String? = null,
    val price: Double? = null,
    val currency: String? = null,
    val store: String? = null,
    val quantity: Int? = null,
    val warranty_until: String? = null,
    val expiration_date: String? = null,
    val manufacturer: String? = null,
    val origin_country: String? = null,
    val location_ids: List<Int>? = null
)
