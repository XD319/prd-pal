import ReviewSubmissionForm from './ReviewSubmissionForm';

function ReviewSubmitPanel(props) {
  return (
    <ReviewSubmissionForm
      {...props}
      kicker="New Review"
      title="Start a review run"
      helperText="Use Document Source when you already have a canonical document reference. Otherwise provide exactly one of PRD Content or File Path."
      submitLabel="Submit review"
      resetLabel="Reset workspace"
      showFilePath
      showLoadSample
    />
  );
}

export default ReviewSubmitPanel;
