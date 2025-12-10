package com.gdemo.data.model

data class DetectionObjectDto(
    val label: String,
    val confidence: Double,
    val bbox: Map<String, Any>?
)

data class DetectionDto(
    val id: Int?,
    val status: String?,
    val objects: List<DetectionObjectDto>?
)

data class MediaDto(
    val id: Int,
    val path: String,
    val mime_type: String?,
    val file_url: String,
    val detection: DetectionDto?
)
