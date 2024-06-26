import logging
import time

import click
from celery import shared_task

from core.rag.index_processor.index_processor_factory import IndexProcessorFactory
from extensions.ext_database import db
from models.dataset import (
    AppDatasetJoin,
    Dataset,
    DatasetProcessRule,
    DatasetQuery,
    Document,
    DocumentSegment,
)


@shared_task(queue='dataset')
def clean_dataset_task(dataset_id: str, tenant_id: str, indexing_technique: str,
                       index_struct: str, collection_binding_id: str, doc_form: str):
    """
    Clean dataset when dataset deleted.
    :param dataset_id: dataset id
    :param tenant_id: tenant id
    :param indexing_technique: indexing technique
    :param index_struct: index struct dict
    :param collection_binding_id: collection binding id
    :param doc_form: dataset form

    Usage: clean_dataset_task.delay(dataset_id, tenant_id, indexing_technique, index_struct)
    """
    logging.info(click.style('Start clean dataset when dataset deleted: {}'.format(dataset_id), fg='green'))
    start_at = time.perf_counter()

    try:
        dataset = Dataset(
            id=dataset_id,
            tenant_id=tenant_id,
            indexing_technique=indexing_technique,
            index_struct=index_struct,
            collection_binding_id=collection_binding_id,
        )
        documents = db.session.query(Document).filter(Document.dataset_id == dataset_id).all()
        segments = db.session.query(DocumentSegment).filter(DocumentSegment.dataset_id == dataset_id).all()

        if documents is None or len(documents) == 0:
            logging.info(click.style('No documents found for dataset: {}'.format(dataset_id), fg='green'))
        else:
            logging.info(click.style('Cleaning documents for dataset: {}'.format(dataset_id), fg='green'))
            index_processor = IndexProcessorFactory(doc_form).init_index_processor()
            index_processor.clean(dataset, None)

            for document in documents:
                db.session.delete(document)

            for segment in segments:
                db.session.delete(segment)

        db.session.query(DatasetProcessRule).filter(DatasetProcessRule.dataset_id == dataset_id).delete()
        db.session.query(DatasetQuery).filter(DatasetQuery.dataset_id == dataset_id).delete()
        db.session.query(AppDatasetJoin).filter(AppDatasetJoin.dataset_id == dataset_id).delete()

        db.session.commit()

        end_at = time.perf_counter()
        logging.info(
            click.style('Cleaned dataset when dataset deleted: {} latency: {}'.format(dataset_id, end_at - start_at), fg='green'))
    except Exception:
        logging.exception("Cleaned dataset when dataset deleted failed")
