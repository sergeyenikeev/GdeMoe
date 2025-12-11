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

data class MediaAnalysisDto(
    val detection_id: Int? = null,
    val detection_ids: List<Int>? = null,
    val status: String? = null
)

data class MediaDto(
    val id: Int,
    val path: String,
    val mime_type: String?,
    val size_bytes: Long? = null,
    val file_hash: String? = null,
    val thumb_path: String? = null,
    val thumb_url: String? = null,
    val file_url: String,
    val detection: DetectionDto? = null,
    val analysis: MediaAnalysisDto? = null
)
