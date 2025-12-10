package com.gdemo.data.model

data class UpdateItemRequest(
    val title: String? = null,
    val status: String? = null,
    val description: String? = null,
    val tags: List<String>? = null,
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
    val location_ids: List<Int>? = null,
    val location_id: Int? = null
)
