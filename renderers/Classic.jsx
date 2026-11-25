import React from 'react';
import {AbsoluteFill, Composition, registerRoot, Sequence} from 'remotion';
import {Slide as RailSlide} from './Pilot.jsx';
import {Slide as OriginalSlide} from './PilotBaseline.jsx';
import {Scene as EditorialScene} from './Edition.jsx';
import {Scene as RedisScene} from './EditionRedis.jsx';

// The published pilot uses the mail rail for the first four chapters.
// The published Redis walkthrough uses the editorial animation except
// for chapter five, which illustrates the conceptual metrics separately.
function Film(props) {
  let start = 0;
  return <AbsoluteFill>{props.slides.map((slide, index) => {
    const from = start;
    start += slide.duration;
    const Scene = props.variant === 'pilot'
      ? index < 4 ? RailSlide : OriginalSlide
      : props.slug === '664114f3' && index === 4 ? RedisScene : EditorialScene;
    return <Sequence key={index} from={from} durationInFrames={slide.duration}>
      <Scene data={props} slide={slide} index={index}/>
    </Sequence>;
  })}</AbsoluteFill>;
}
const duration = ({props}) => ({
  durationInFrames: props.slides.reduce((total, slide) => total + slide.duration, 0) || 16,
});
registerRoot(() => <>
  <Composition id="ArticleFilm" component={Film} defaultProps={{slides:[], variant:'pilot'}}
    width={1280} height={720} fps={24} durationInFrames={24} calculateMetadata={duration}/>
  <Composition id="EditorialArticle" component={Film} defaultProps={{slides:[]}}
    width={1280} height={720} fps={16} durationInFrames={16} calculateMetadata={duration}/>
</>);
