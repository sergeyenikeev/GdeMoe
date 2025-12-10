package com.gdemo.data.model

data class LocationCreateRequest(
    val name: String,
    val workspace_id: Int = 2,
    val kind: String = "other",
    val parent_id: Int? = null
)

data class LocationUpdateRequest(
    val name: String? = null,
    val kind: String? = null,
    val parent_id: Int? = null
)
