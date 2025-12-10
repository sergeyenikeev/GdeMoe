package com.gdemo.data.model

data class Item(
    val id: Int,
    val title: String,
    val status: String,
    val description: String? = null,
    val category: String? = null,
    val attributes: Map<String, Any?>? = null,
    val links: List<String>? = null,
    val store: String? = null,
    val price: Double? = null,
    val currency: String? = null,
    val purchase_datetime: String? = null,
    val warranty_until: String? = null,
    val expiration_date: String? = null,
    val quantity: Int? = null,
    val manufacturer: String? = null,
    val origin_country: String? = null,
    val location_ids: List<Int>? = null,
    val purchase_date: String? = null,
    val tags: List<String> = emptyList(),
    val location: String? = null,
    val thumbnail: String? = null,
    val needsReview: Boolean = false
)

data class LocationNode(
    val id: String,
    val name: String,
    val children: List<LocationNode> = emptyList()
)
