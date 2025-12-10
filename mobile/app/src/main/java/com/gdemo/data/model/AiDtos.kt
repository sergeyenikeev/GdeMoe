package com.gdemo.data.model

data class AiDetectionObjectDto(
    val id: Int,
    val label: String,
    val confidence: Double,
    val bbox: Map<String, Any?>? = null,
    val suggested_location_id: Int? = null,
    val decision: String,
    val candidates: List<Map<String, Any?>> = emptyList()
)

data class AiDetectionDto(
    val id: Int,
    val media_id: Int,
    val status: String,
    val created_at: String,
    val completed_at: String?,
    val media_path: String?,
    val thumb_path: String?,
    val objects: List<AiDetectionObjectDto> = emptyList()
)

data class AiDetectionActionRequest(
    val item_id: Int? = null,
    val location_id: Int? = null
)

data class AiDetectionReviewLogRequest(
    val action: String,
    val payload: Map<String, Any?>? = null
)
