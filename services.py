import copy
from datetime import datetime
from django.db import transaction
from shared.common.constant import DocumentConstant, ChecklistStep
from ios.common.internal_response import InternalResponse
from ios.common.message_code import MessageCode
from ios.common.services.document_service import DocumentService
from ios.common.services.user_service import UserService
from ios.common.shared_utils import get_success_msg
from ios.external_partner.mappers import PartnerMapper
from shared.helper.logger_helper import logger_info, logger_exception


class PartnerService:
    def __init__(self, user_pk, user_source_id):
        self.user_pk = user_pk
        self.user_source_id = user_source_id
        self.mapper = PartnerMapper(
            user_pk=user_pk, user_source_id=user_source_id
        )

        self.external_partner_checklist_steps = \
            ChecklistStep.EXTERNAL_INVESTOR_CHECKLIST

    def get_channel_partner_id(self):
        return self.mapper.get_channel_partner_id()

    def is_checklist_valid_for_legal_authorization(self, checklist):
        try:
            user_completed_step = checklist.get('completed_steps')
            cp_investor_checklist = copy.deepcopy(
                self.external_partner_checklist_steps
            )
            cp_investor_checklist.remove(ChecklistStep.LEGAL_AUTHORIZATION)
            if set(cp_investor_checklist).issubset(user_completed_step):
                return True
            return False

        except Exception:
            return False

    def process_legal_authorization(self, user_source_id, user_pk, user_id,
                                    source):

        try:
            logger_info('Processing legal authorization for user',
                        {"user_id":user_id})

            user_service = UserService(
                user_pk=user_pk, user_source_id=user_source_id
            )
            user_checklist = user_service.fetch_user_checklist()

            if ChecklistStep.LEGAL_AUTHORIZATION in user_checklist['completed_steps']:
                logger_info('Legal authorization already completed for user',
                            {"user_id":user_id})
                return InternalResponse(message=get_success_msg(
                    MessageCode.CODE_001001)
                )

            if not self.is_checklist_valid_for_legal_authorization(user_checklist):
                logger_info('Legal authorization prerequisites not met for user',
                            {"user_id":user_id})
                return InternalResponse(code=MessageCode.CODE_000011)

            with transaction.atomic():
                agreement_type = DocumentConstant.TERMS_AND_CONDITIONS

                user_service.insert_legal_auth_data()
                user_service.create_investor_timeline(agreement_type)

                user_data = user_service.get_user()

                user_first_name = user_data['first_name']

                context = {
                    'name': user_first_name,
                    'lender_id': user_id,
                    'acceptance_date': datetime.today()
                }

                document_service = DocumentService(
                    user_source_id=user_source_id, user_pk=user_pk
                )

                is_documents_uploaded = \
                    document_service.accept_and_store_legal_and_rbi_document(
                        context=context
                    )

                if not is_documents_uploaded.is_valid:
                    logger_info('Error occurred while uploading documents for user',
                                {"user_id":user_id})
                    raise Exception("Error occurred while uploading documents")

                completed_step = ChecklistStep.LEGAL_AUTHORIZATION

                user_service.check_and_update_completed_step(
                    step_name=completed_step
                )

                aml_check_result = UserService(user_pk, user_source_id).check_aml(
                    source=source)
                if not aml_check_result.is_valid:
                    return aml_check_result

                return InternalResponse(message=get_success_msg(
                    MessageCode.CODE_001000)
                )

        except Exception as e:
            logger_exception(e)
            return InternalResponse(code=MessageCode.CODE_000012)