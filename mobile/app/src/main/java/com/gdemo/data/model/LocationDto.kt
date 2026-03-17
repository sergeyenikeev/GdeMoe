package com.gdemo.data.model

data class LocationDto(
    val id: Int,
    val name: String,
    val parent_id: Int?,
    val kind: String?,
    val path: String?,
    val photo_media_id: Int? = null
)
