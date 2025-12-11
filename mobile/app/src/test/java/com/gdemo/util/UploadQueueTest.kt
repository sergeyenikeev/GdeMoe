package com.gdemo.util

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class UploadQueueTest {
    private val dispatcher = StandardTestDispatcher()

    @Test
    fun taskSucceeds() = runTest(dispatcher) {
        val queue = UploadQueue(scope = this, maxRetries = 3, baseDelayMs = 1)
        queue.enqueue("ok") { true }
        dispatcher.scheduler.advanceUntilIdle()
        val last = queue.tasks.value.last()
        assertEquals(UploadQueue.Status.SUCCESS, last.status)
        assertEquals(1, last.attempts)
    }

    @Test
    fun taskRetriesThenSucceeds() = runTest(dispatcher) {
        val queue = UploadQueue(scope = this, maxRetries = 3, baseDelayMs = 1)
        var counter = 0
        queue.enqueue("flaky") {
            counter += 1
            counter >= 2
        }
        dispatcher.scheduler.advanceUntilIdle()
        val last = queue.tasks.value.last()
        assertEquals(UploadQueue.Status.SUCCESS, last.status)
        assertTrue(last.attempts >= 2)
    }

    @Test
    fun taskFailsAfterRetries() = runTest(dispatcher) {
        val queue = UploadQueue(scope = this, maxRetries = 2, baseDelayMs = 1)
        queue.enqueue("fail") { false }
        dispatcher.scheduler.advanceUntilIdle()
        val last = queue.tasks.value.last()
        assertEquals(UploadQueue.Status.FAILED, last.status)
        assertEquals(2, last.attempts)
    }
}
