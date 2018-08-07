#
# Copyright (C) 2018 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging

from vts.proto import AndroidSystemControlMessage_pb2 as ASysCtrlMsg
from vts.proto import VtsResourceControllerMessage_pb2 as ResControlMsg
from vts.proto import ComponentSpecificationMessage_pb2 as CompSpecMsg
from vts.utils.python.mirror import mirror_object


class ResourceFmqMirror(mirror_object.MirrorObject):
    """This is a class that mirrors FMQ resource allocated on the target side.

    Attributes:
        _client: the TCP client instance.
        _queue_id: int, used to identify the queue object on the target side.
        _data_type: type of data in the queue.
        _sync: bool, whether the queue is synchronized.
    """

    def __init__(self, client, queue_id=-1):
        super(ResourceFmqMirror, self).__init__(client)
        self._queue_id = queue_id

    def _create(self, data_type, sync, queue_id, queue_size, blocking,
                reset_pointers):
        """Initiate a fast message queue object on the target side,
           and stores the queue_id in the class attribute.
           User should not directly call this method because it will overwrite
           the original queue_id stored in the mirror object, leaving that
           queue object out of reference.
           User should always call InitFmq() in mirror_tracker.py to obtain a
           new queue object.

        Args:
            data_type: string, type of data in the queue (e.g. "uint32_t", "int16_t").
            sync: bool, whether queue is synchronized (only has one reader).
            queue_id: int, identifies the message queue object on the target side.
            queue_size: int, size of the queue.
            blocking: bool, whether blocking is enabled in the queue.
            reset_pointers: bool, whether to reset read/write pointers when
              creating a message queue object based on an existing message queue.
        """
        # Sets some configuration for the current resource mirror.
        self._data_type = data_type
        self._sync = sync

        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_CREATE, queue_id)
        request_msg.queue_size = queue_size
        request_msg.blocking = blocking
        request_msg.reset_pointers = reset_pointers

        # Send and receive data.
        fmq_response = self._client.SendFmqRequest(request_msg)
        if fmq_response is not None and fmq_response.queue_id != -1:
            self._queue_id = fmq_response.queue_id
        else:
            self._queue_id = -1
            logging.error("Failed to create a new queue object.")

    def read(self, data, data_size):
        """Initiate a non-blocking read request to FMQ driver.

        Args:
            data: list, data to be filled by this function. The list will
                  be emptied before the function starts to put read data into
                  it, which is consistent with the function behavior on the
                  target side.
            data_size: int, length of data to read.

        Returns:
            bool, true if the operation succeeds,
                  false otherwise.
        """
        # Prepare arguments.
        del data[:]
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_READ, self._queue_id)
        request_msg.read_data_size = data_size

        # Send and receive data.
        fmq_response = self._client.SendFmqRequest(request_msg)
        if fmq_response is not None and fmq_response.success:
            self._extractReadData(fmq_response, data)
            return True
        return False

    # TODO: support long-form blocking read in the future when there is use case.
    def readBlocking(self, data, data_size, time_out_nanos=0):
        """Initiate a blocking read request (short-form) to FMQ driver.

        Args:
            data: list, data to be filled by this function. The list will
                  be emptied before the function starts to put read data into
                  it, which is consistent with the function behavior on the
                  target side.
            data_size: int, length of data to read.
            time_out_nanos: int, wait time (in nanoseconds) when blocking.
                            The default value is 0 (no blocking).

        Returns:
            bool, true if the operation succeeds,
                  false otherwise.
        """
        # Prepare arguments.
        del data[:]
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_READ_BLOCKING, self._queue_id)
        request_msg.read_data_size = data_size
        request_msg.time_out_nanos = time_out_nanos

        # Send and receive data.
        fmq_response = self._client.SendFmqRequest(request_msg)
        if fmq_response is not None and fmq_response.success:
            self._extractReadData(fmq_response, data)
            return True
        return False

    def write(self, data, data_size):
        """Initiate a non-blocking write request to FMQ driver.

        Args:
            data: list, data to be written.
            data_size: int, length of data to write.
                       The function will only write data up until data_size,
                       i.e. extraneous data will be discarded.

        Returns:
            bool, true if the operation succeeds,
                  false otherwise.
        """
        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_WRITE, self._queue_id)
        self._prepareWriteData(request_msg, data[:data_size])

        # Send and receive data.
        fmq_response = self._client.SendFmqRequest(request_msg)
        if fmq_response is not None:
            return fmq_response.success
        return False

    # TODO: support long-form blocking write in the future when there is use case.
    def writeBlocking(self, data, data_size, time_out_nanos=0):
        """Initiate a blocking write request (short-form) to FMQ driver.

        Args:
            data: list, data to be written.
            data_size: int, length of data to write.
                       The function will only write data up until data_size,
                       i.e. extraneous data will be discarded.
            time_out_nanos: int, wait time (in nanoseconds) when blocking.
                            The default value is 0 (no blocking).

        Returns:
            bool, true if the operation succeeds,
                  false otherwise.
        """
        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_WRITE_BLOCKING, self._queue_id)
        self._prepareWriteData(request_msg, data[:data_size])
        request_msg.time_out_nanos = time_out_nanos

        # Send and receive data.
        fmq_response = self._client.SendFmqRequest(request_msg)
        if fmq_response is not None:
            return fmq_response.success
        return False

    def availableToWrite(self):
        """Gets space available to write in the queue.

        Returns:
            int, number of slots available.
        """
        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_AVAILABLE_WRITE, self._queue_id)

        # Send and receive data.
        return self._processUtilMethod(request_msg)

    def availableToRead(self):
        """Gets number of items available to read.

        Returns:
            int, number of items.
        """
        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_AVAILABLE_READ, self._queue_id)

        # Send and receive data.
        return self._processUtilMethod(request_msg)

    def getQuantumSize(self):
        """Gets size of item in the queue.

        Returns:
            int, size of item.
        """
        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_GET_QUANTUM_SIZE, self._queue_id)

        # send and receive data
        return self._processUtilMethod(request_msg)

    def getQuantumCount(self):
        """Gets number of items that fit in the queue.

        Returns:
            int, number of items.
        """
        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_GET_QUANTUM_COUNT, self._queue_id)

        # Send and receive data.
        return self._processUtilMethod(request_msg)

    def isValid(self):
        """Check if the queue is valid.

        Returns:
            bool, true if the queue is valid.
        """
        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.FMQ_PROTO_IS_VALID, self._queue_id)

        # Send and receive data.
        fmq_response = self._client.SendFmqRequest(request_msg)
        if fmq_response is not None:
            return fmq_response.success
        return False

    def getQueueId(self):
        """Gets the id assigned from the target side.

        Returns:
            int, id of the queue.
        """
        return self._queue_id

    def _createTemplateRequestMessage(self, operation, queue_id):
        """Creates a template FmqRequestMessage with common arguments among
           all FMQ operations.

        Args:
            operation: FmqOp, fmq operations.
                       (see test/vts/proto/VtsResourceControllerMessage.proto).
            queue_id: int, identifies the message queue object on target side.

        Returns:
            FmqRequestMessage, fmq request message.
                (See test/vts/proto/VtsResourceControllerMessage.proto).
        """
        request_msg = ResControlMsg.FmqRequestMessage()
        request_msg.operation = operation
        request_msg.data_type = self._data_type
        request_msg.sync = self._sync
        request_msg.queue_id = queue_id
        return request_msg

    # Converts a python list into protobuf message.
    # TODO: Consider use py2pb once we know how to support user-defined types.
    #       This method only supports primitive types like int32_t, bool_t.
    def _prepareWriteData(self, request_msg, data):
        """Prepares write data by converting python list into
           repeated protobuf field.

        Args:
            request_msg: FmqRequestMessage, arguments for a FMQ operation request.
            data: list, list of data items.
        """
        for curr_value in data:
            new_message = request_msg.write_data.add()
            new_message.type = CompSpecMsg.TYPE_SCALAR
            new_message.scalar_type = self._data_type
            setattr(new_message.scalar_value, self._data_type, curr_value)

    def _extractReadData(self, response_msg, data):
        """Extracts read data from the response message returned by client.

        Args:
            response_msg: FmqResponseMessage, contains response from FMQ driver.
            data: list, to be filled by this function. data buffer is provided
                  by caller, so this function will append every element to the
                  buffer.
        """
        for item in response_msg.read_data:
            data.append(self._client.GetPythonDataOfVariableSpecMsg(item))

    def _processUtilMethod(self, request_msg):
        """Sends request message and process response message for util methods
           that return an unsigned integer,
           e.g. availableToWrite, availableToRead.

        Args:
            request_msg: FmqRequestMessage, arguments for a FMQ operation request.

        Returns: int, information about the queue,
                 None if the operation is unsuccessful.
        """
        fmq_response = self._client.SendFmqRequest(request_msg)
        if fmq_response is not None and fmq_response.success:
            return fmq_response.sizet_return_val
        return None


class ResourceHidlMemoryMirror(mirror_object.MirrorObject):
    """This class mirrors hidl_memory resource allocated on the target side.

    Attributes:
        _client: the TCP client instance.
        _mem_id: int, used to identify the memory region on the target side.
    """

    def __init__(self, client, mem_id=-1):
        super(ResourceHidlMemoryMirror, self).__init__(client)
        self._mem_id = mem_id

    def _allocate(self, mem_size):
        """Initiate a hidl_memory region on the target side.

        This method stores the mem_id in the class attribute.
        Users should not directly call this method to get a new memory region,
        because it will overwrite the original memory object with mem_id,
        making that memory object out of reference.
        Users should always call InitHidlMemory() in mirror_tracker.py to get
        a new memory region.

        Args:
            mem_size: int, size of the requested memory region.
        """
        # Prepare arguments.
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_ALLOCATE)
        request_msg.mem_size = mem_size

        # Send and receive data.
        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None and response_msg.new_mem_id != -1:
            self._mem_id = response_msg.new_mem_id
        else:
            logging.error("Failed to allocate memory region.")

    def read(self):
        """Notify that caller will read the entire memory region.

        Before every actual read operation, caller must call this method
        or readRange() first.

        Returns:
            bool, true if the operation succeeds, false otherwise.
        """
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_START_READ)

        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None:
            if not response_msg.success:
                logging.error("Failed to find memory region with id %d",
                              self._mem_id)
            return response_msg.success
        return False

    def readRange(self, start, length):
        """Notify that caller will read only part of memory region.

        Notify that caller will read starting at start and
        ending at start + length.
        Before every actual read operation, caller must call this method
        or read() first.

        Args:
            start: int, offset from the start of memory region to be modified.
            length: int, number of bytes to be modified.

        Returns:
            bool, true if the operation succeeds, false otherwise.
        """
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_START_READ_RANGE)
        request_msg.start = start
        request_msg.length = length

        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None:
            if not response_msg.success:
                logging.error("Failed to find memory region with id %d",
                              self._mem_id)
            return response_msg.success
        return False

    def update(self):
        """Notify that caller will possibly write to all memory region.

        Before every actual write operation, caller must call this method
        or updateRange() first.

        Returns:
            bool, true if the operation succeeds, false otherwise.
        """
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_START_UPDATE)

        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None:
            if not response_msg.success:
                logging.error("Failed to find memory region with id %d",
                              self._mem_id)
            return response_msg.success
        return False

    def updateRange(self, start, length):
        """Notify that caller will only write to part of memory region.

        Notify that caller will only write starting at start and
        ending at start + length.
        Before every actual write operation, caller must call this method
        or update() first.

        Args:
            start: int, offset from the start of memory region to be modified.
            length: int, number of bytes to be modified.

        Returns:
            bool, true if the operation succeeds, false otherwise.
        """
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_START_UPDATE_RANGE)
        request_msg.start = start
        request_msg.length = length

        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None:
            if not response_msg.success:
                logging.error("Failed to find memory region with id %d",
                              self._mem_id)
            return response_msg.success
        return False

    def readBytes(self, length, start=0):
        """This method performs actual read operation.

        This method helps caller perform actual read operation on the
        memory region, because host side won't be able to cast c++ pointers.

        Args:
            length: int, number of bytes to read.
            start: int, offset from the start of memory region to read.

        Returns:
            string, data read from memory.
                    Caller can perform conversion on the result to obtain the
                    corresponding data structure in python.
            None, indicate if the read fails.
        """
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_READ_BYTES)
        request_msg.start = start
        request_msg.length = length

        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None:
            if response_msg.success:
                return response_msg.read_data
            logging.error("Failed to find memory region with id %d",
                          self._mem_id)
        return None

    def updateBytes(self, data, length, start=0):
        """This method performs actual write operation.

        This method helps caller perform actual write operation on the
        memory region, because host side won't be able to cast c++ pointers.

        Args:
            data: string, bytes to be written into memory.
                  Caller can use bytearray() function to convert python
                  data structures into python, and call str() on the resulting
                  bytearray object.
            length: int, number of bytes to write.
            start: int, offset from the start of memory region to be modified.

        Returns:
            bool, true if the operation succeeds, false otherwise.
        """
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_UPDATE_BYTES)
        request_msg.write_data = data
        request_msg.start = start
        request_msg.length = length

        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None:
            if not response_msg.success:
                logging.error("Failed to find memory region with id %d",
                              self._mem_id)
            return response_msg.success
        return False

    def commit(self):
        """Caller signals done with operating on the memory region.

        Caller needs to call this method after reading/writing.

        Returns:
            bool, true if the operation succeeds, false otherwise.
        """
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_COMMIT)

        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None:
            if not response_msg.success:
                logging.error("Failed to find memory region with id %d",
                              self._mem_id)
            return response_msg.success
        return False

    def getSize(self):
        """Gets the size of the memory region.

        Returns:
            int, size of memory region, -1 to signal operation failure.
        """
        request_msg = self._createTemplateRequestMessage(
            ResControlMsg.MEM_PROTO_GET_SIZE)

        response_msg = self._client.SendHidlMemoryRequest(request_msg)
        if response_msg is not None:
            if response_msg.success:
                return response_msg.mem_size
            logging.error("Failed to find memory region with id %d",
                          self._mem_id)
        return -1

    def getMemId(self):
        """Gets the id assigned from the target side.

        Returns:
            int, id of the memory object.
        """
        return self._mem_id

    def _createTemplateRequestMessage(self, operation):
        """Creates a template HidlMemoryRequestMessage.

        This method creates a message that contains common arguments among
        all hidl_memory operations.

        Args:
            operation: HidlMemoryOp, hidl_memory operations.
                       (see test/vts/proto/VtsResourceControllerMessage.proto).

        Returns:
            HidlMemoryRequestMessage, hidl_memory request message.
                (See test/vts/proto/VtsResourceControllerMessage.proto).
        """
        request_msg = ResControlMsg.HidlMemoryRequestMessage()
        request_msg.operation = operation
        request_msg.mem_id = self._mem_id
        return request_msg