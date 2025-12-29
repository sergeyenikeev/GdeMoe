package com.gdemo.data.model

data class UploadHistoryEntryDto(
    val id: Int,
    val media_id: Int?,
    val workspace_id: Int,
    val owner_user_id: Int,
    val location_id: Int? = null,
    val media_type: String,
    val status: String,
    val source: String?,
    val ai_status: String?,
    val ai_summary: Map<String, Any?>?,
    val path: String?,
    val thumb_path: String?,
    val file_url: String?,
    val thumb_url: String?,
    val detection_id: Int?,
    val objects: List<AiDetectionObjectDto> = emptyList(),
    val created_at: String
)
