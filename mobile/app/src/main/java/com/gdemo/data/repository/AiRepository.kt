package com.gdemo.data.repository

import com.gdemo.data.model.AiDetectionActionRequest
import com.gdemo.data.model.AiDetectionDto
import com.gdemo.data.model.AiDetectionReviewLogRequest
import com.gdemo.data.remote.ApiService
import com.gdemo.data.model.UploadHistoryEntryDto
import com.gdemo.data.model.AiDetectionObjectDto
import com.gdemo.data.model.AiDetectionObjectUpdateRequest

class AiRepository(private val api: ApiService) {
    suspend fun pending(): List<AiDetectionDto> = api.aiDetections()

    suspend fun accept(id: Int, itemId: Int? = null, locationId: Int? = null): AiDetectionDto =
        api.acceptDetection(id, AiDetectionActionRequest(item_id = itemId, location_id = locationId))

    suspend fun reject(id: Int, itemId: Int? = null, locationId: Int? = null): AiDetectionDto =
        api.rejectDetection(id, AiDetectionActionRequest(item_id = itemId, location_id = locationId))

    suspend fun log(id: Int, action: String, payload: Map<String, Any?>? = null) {
        api.addDetectionLog(id, AiDetectionReviewLogRequest(action = action, payload = payload))
    }

    suspend fun history(limit: Int = 50): List<UploadHistoryEntryDto> = api.uploadHistory(limit)

    suspend fun updateObject(
        objectId: Int,
        itemId: Int? = null,
        locationId: Int? = null,
        decision: String? = null
    ): AiDetectionObjectDto = api.updateDetectionObject(
        objectId,
        AiDetectionObjectUpdateRequest(item_id = itemId, location_id = locationId, decision = decision)
    )
}
