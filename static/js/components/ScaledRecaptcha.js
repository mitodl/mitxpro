// @flow
import React from "react"
import ReCAPTCHA from "react-google-recaptcha"
import styled from "styled-components"
import debounce from "lodash/debounce"

type Props = {
  onRecaptcha: Function,
  recaptchaKey: string
}

type State = {
  recaptchaScale: number
}

// These needs to stay in sync with ReCAPTCHA's runtime width
const RECAPTCHA_NATURAL_WIDTH = 304
const RECAPTCHA_NATURAL_HEIGHT = 78

const StyledReCAPTCHA = styled(ReCAPTCHA)`
  transform: scale(${props => props.scale.toFixed(3)});
  transform-origin: 0 0;
  height: ${props => (props.scale * RECAPTCHA_NATURAL_HEIGHT).toFixed(0)}px;
`

export default class ScaledRecaptcha extends React.Component<Props, State> {
  recaptcha: null

  constructor(props: Props) {
    window.recaptchaOptions = {
      useRecaptchaNet: true
    }
    super(props)
    // use old-style ref so we can resize when it mounts
    this.recaptcha = null
    // only rescale up to 4x a second to salvage some performance
    this.scaleRecaptcha = debounce(this.scaleRecaptcha.bind(this), 250)
    this.state = {
      recaptchaScale: 1.0
    }
  }

  componentDidMount() {
    window.addEventListener("resize", this.scaleRecaptcha)
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.scaleRecaptcha)
  }

  scaleRecaptcha = () => {
    if (this.recaptcha) {
      const {
        captcha: { clientWidth }
      } = this.recaptcha
      // compute this as a fractional scale of the scale that ReCAPTCHA wants to render at if our container is smaller
      const recaptchaScale =
        clientWidth < RECAPTCHA_NATURAL_WIDTH
          ? clientWidth / RECAPTCHA_NATURAL_WIDTH
          : 1.0

      this.setState({ recaptchaScale })
    }
  }

  setRecaptcha = (recaptcha: any) => {
    this.recaptcha = recaptcha
    this.scaleRecaptcha()
  }

  render() {
    const { recaptchaKey, onRecaptcha } = this.props
    const { recaptchaScale } = this.state

    return (
      <StyledReCAPTCHA
        ref={this.setRecaptcha}
        sitekey={recaptchaKey}
        onChange={onRecaptcha}
        scale={recaptchaScale}
      />
    )
  }
}
